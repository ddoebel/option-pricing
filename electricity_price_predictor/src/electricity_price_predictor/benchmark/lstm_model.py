"""Sequence LSTM regressor with scaling, DataLoader, and optional early stopping."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from .data_prep import TabularModelFrame


def create_sequences(
    X: np.ndarray, y: np.ndarray, seq_len: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build supervised sequences: X_seq[i] = rows [i : i+seq_len), y_seq[i] = y[i+seq_len].

    Returns ``(X_seq, y_seq, target_row_index)`` where ``target_row_index[i] = i + seq_len``.
    """
    n = len(X)
    if n <= seq_len:
        raise ValueError(f"Need len(X) > seq_len; got n={n}, seq_len={seq_len}")
    X_seq, y_seq, idx = [], [], []
    for i in range(n - seq_len):
        X_seq.append(X[i : i + seq_len])
        y_seq.append(y[i + seq_len])
        idx.append(i + seq_len)
    return np.asarray(X_seq, dtype=np.float32), np.asarray(y_seq, dtype=np.float32), np.asarray(idx, dtype=np.int64)


def _split_sequence_indices(target_row_index: np.ndarray, train_end: int, valid_end: int) -> tuple[np.ndarray, ...]:
    """Assign each sequence to train/valid/test by the index of its prediction target row."""
    train_mask = target_row_index < train_end
    valid_mask = (target_row_index >= train_end) & (target_row_index < valid_end)
    test_mask = target_row_index >= valid_end
    return np.where(train_mask)[0], np.where(valid_mask)[0], np.where(test_mask)[0]


class LSTMModel(nn.Module):
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        num_layers: int = 1,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last = out[:, -1, :]
        last = self.dropout(last)
        return self.fc(last)


@dataclass
class LSTMBenchmarkArtifacts:
    model: LSTMModel
    scaler_X: StandardScaler
    scaler_y: StandardScaler
    seq_len: int
    device: torch.device


def _fit_scalers(
    X_train_seq: np.ndarray, y_train_seq: np.ndarray
) -> tuple[StandardScaler, StandardScaler]:
    n, seq, n_feat = X_train_seq.shape
    scaler_X = StandardScaler()
    scaler_X.fit(X_train_seq.reshape(-1, n_feat))
    scaler_y = StandardScaler()
    scaler_y.fit(y_train_seq.reshape(-1, 1))
    return scaler_X, scaler_y


def _transform_sequences(scaler_X: StandardScaler, X: np.ndarray) -> np.ndarray:
    n, seq, n_feat = X.shape
    flat = X.reshape(-1, n_feat)
    return scaler_X.transform(flat).reshape(n, seq, n_feat).astype(np.float32)


def train_lstm_benchmark(
    prep: TabularModelFrame,
    train_end: int,
    valid_end: int,
    *,
    seq_len: int = 24,
    hidden_size: int = 64,
    num_layers: int = 1,
    dropout: float = 0.2,
    batch_size: int = 64,
    epochs: int = 50,
    lr: float = 1e-3,
    early_stopping_patience: int = 8,
    device: torch.device | None = None,
) -> tuple[LSTMBenchmarkArtifacts, dict[str, float], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Train LSTM on sequences whose prediction target falls strictly before ``train_end``;
    monitor loss on validation sequences.

    Returns ``(artifacts, timing, X_seq, y_seq, va_ix, te_ix)`` for reuse in benchmarks
    (``va_ix`` / ``te_ix`` index rows of ``X_seq`` / ``y_seq``).
    """
    import time

    df = prep.df_model
    feature_cols = prep.feature_cols
    target_col = prep.target_col

    X_arr = df[feature_cols].to_numpy(dtype=np.float32)
    y_arr = df[target_col].to_numpy(dtype=np.float32)

    X_seq, y_seq, tgt_idx = create_sequences(X_arr, y_arr, seq_len)
    tr_ix, va_ix, te_ix = _split_sequence_indices(tgt_idx, train_end, valid_end)
    if len(tr_ix) == 0 or len(va_ix) == 0 or len(te_ix) == 0:
        raise ValueError(
            f"Insufficient sequences for LSTM split: train={len(tr_ix)}, valid={len(va_ix)}, "
            f"test={len(te_ix)} (try longer history or smaller seq_len)."
        )

    X_tr, y_tr = X_seq[tr_ix], y_seq[tr_ix]
    X_va, y_va = X_seq[va_ix], y_seq[va_ix]

    scaler_X, scaler_y = _fit_scalers(X_tr, y_tr)
    X_tr_t = _transform_sequences(scaler_X, X_tr)
    X_va_t = _transform_sequences(scaler_X, X_va)

    y_tr_t = scaler_y.transform(y_tr.reshape(-1, 1)).ravel().astype(np.float32)
    y_va_t = scaler_y.transform(y_va.reshape(-1, 1)).ravel().astype(np.float32)

    dev = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_feat = X_tr_t.shape[2]
    model = LSTMModel(n_feat, hidden_size=hidden_size, num_layers=num_layers, dropout=dropout).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    train_ds = TensorDataset(
        torch.from_numpy(X_tr_t),
        torch.from_numpy(y_tr_t),
    )
    valid_ds = TensorDataset(
        torch.from_numpy(X_va_t),
        torch.from_numpy(y_va_t),
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    valid_loader = DataLoader(valid_ds, batch_size=batch_size, shuffle=False)

    best_state = None
    best_val = float("inf")
    stall = 0

    t0 = time.perf_counter()
    for epoch in range(epochs):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad()
            pred = model(xb).squeeze(-1)
            loss = loss_fn(pred, yb)
            loss.backward()
            opt.step()

        model.eval()
        val_losses = []
        with torch.no_grad():
            for xb, yb in valid_loader:
                xb, yb = xb.to(dev), yb.to(dev)
                pred = model(xb).squeeze(-1)
                val_losses.append(loss_fn(pred, yb).item())
        val_m = float(np.mean(val_losses)) if val_losses else float("inf")
        if val_m < best_val - 1e-6:
            best_val = val_m
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stall = 0
        else:
            stall += 1
            if stall >= early_stopping_patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    train_time = time.perf_counter() - t0

    art = LSTMBenchmarkArtifacts(
        model=model,
        scaler_X=scaler_X,
        scaler_y=scaler_y,
        seq_len=seq_len,
        device=dev,
    )
    return art, {"train_time": train_time}, X_seq, y_seq, va_ix, te_ix


def predict_lstm(artifacts: LSTMBenchmarkArtifacts, X_seq: np.ndarray) -> np.ndarray:
    """Predict on scaled sequences; returns original-scale targets."""
    model = artifacts.model
    dev = artifacts.device
    X_t = _transform_sequences(artifacts.scaler_X, X_seq)
    model.eval()
    with torch.no_grad():
        tens = torch.from_numpy(X_t).to(dev)
        pred_scaled = model(tens).squeeze(-1).cpu().numpy()
    return artifacts.scaler_y.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()
