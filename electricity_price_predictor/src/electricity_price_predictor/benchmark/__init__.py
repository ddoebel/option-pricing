"""Benchmarking utilities: GAM+AR(1), LightGBM, LSTM, metrics, and suite runner."""

from .data_prep import TabularModelFrame, prepare_tabular_model_frame, time_series_split_ends
from .gam_ar1 import GamAr1AdditiveModel, compute_additive_model_gam_ar1
from .lightgbm_model import LightGBMBenchmarkResult, print_lightgbm_metrics, train_lightgbm_benchmark
from .lstm_model import LSTMBenchmarkArtifacts, LSTMModel, create_sequences, predict_lstm, train_lstm_benchmark
from .metrics import benchmark_model, mae_rmse
from .suite import run_benchmark_suite

__all__ = [
    "TabularModelFrame",
    "GamAr1AdditiveModel",
    "LSTMBenchmarkArtifacts",
    "LSTMModel",
    "LightGBMBenchmarkResult",
    "benchmark_model",
    "compute_additive_model_gam_ar1",
    "create_sequences",
    "mae_rmse",
    "predict_lstm",
    "prepare_tabular_model_frame",
    "print_lightgbm_metrics",
    "run_benchmark_suite",
    "time_series_split_ends",
    "train_lightgbm_benchmark",
    "train_lstm_benchmark",
]
