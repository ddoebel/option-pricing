# Quant Finance Hybrid Project — Requirements Elicitation + Mathematical Specification (C++ Core, Python Research Layer)

**Project codename:** `quant-engine`  
**Goal:** Build a reproducible, testable, performance-aware pricing library for European options under Black–Scholes, with Monte Carlo (MC) as the primary numerical method, and an optional PDE/FEM track for cross-validation and CSE-grade numerical analysis.

---

## 1. Stakeholders and Intended Use

### 1.1 Primary stakeholder
- **You (developer/researcher):** want a sustainable workflow: derivations → implementation → verification → benchmarking → reporting.

### 1.2 Secondary stakeholders (implicit)
- **Course staff / graders:** expect numerics rigor (convergence, stability, error bars), clean code structure, and evidence of understanding.
- **Recruiters / interviewers (optional):** expect engineering maturity (modular design, tests, profiling) and mathematical correctness.

### 1.3 Use cases
1. Price a European call/put via Monte Carlo with confidence intervals.
2. Compute Greeks (Delta, Vega) with stable estimators.
3. Reduce variance via antithetic + control variates; quantify variance reduction.
4. Benchmark performance (single-thread vs multi-thread; C++ vs Python wrapper).
5. (Optional) Solve Black–Scholes PDE numerically (FD or FEM) and compare to MC and analytic pricing.

---

## 2. Scope and Non-Scope

### 2.1 In-scope (baseline)
- Black–Scholes risk-neutral dynamics
- European options (call/put)
- MC pricing with error estimation
- Variance reduction: antithetic variates, control variates
- Greeks: Delta, Vega via pathwise derivative
- Deterministic validation against closed-form Black–Scholes formula
- Clean C++ library with a small CLI runner and Python experiment scripts

### 2.2 In-scope (advanced extensions)
- Quasi-MC (Sobol) optional
- OpenMP parallel MC
- Calibration (implied vol) optional
- PDE solver (FD or FEM/Galerkin) optional for cross-validation

### 2.3 Explicit non-scope (for now)
- Exotic options requiring full path simulation (barrier/asian) **unless** you later extend
- Jump-diffusion, local vol, Heston calibration (future phases)
- Full market data infrastructure (DB ingestion, tick-level)

---

## 3. Deliverables

### 3.1 Code deliverables
- `libqengine` (C++): pricing + Greeks + variance reduction
- `qengine_cli` (C++): command-line program to run experiments
- `pyqengine` (Python layer): plotting + experiment orchestration (optional binding via pybind11)
- Test suite (unit + numerical regression tests)
- Benchmark scripts + reproducible configs

### 3.2 Documentation deliverables
- A technical report in Markdown/LaTeX including:
    - model assumptions
    - derivations
    - estimator definitions
    - error/variance analysis
    - convergence plots
    - performance benchmarks
    - limitations + future work

---

## 4. Mathematical Model Specification

### 4.1 Risk-neutral model (Black–Scholes)
Under the risk-neutral measure $\mathbb{Q}$,
$$
dS_t = r S_t\,dt + \sigma S_t\,dW_t,
$$
where:
- $S_t > 0$ is the asset price
- $r$ is the continuously-compounded risk-free rate
- $\sigma > 0$ is volatility
- $W_t$ is standard Brownian motion.

### 4.2 Terminal distribution (exact sampling)
Apply Itô’s lemma to $\log S_t$:
$$
d(\log S_t) = \left(r - \tfrac12\sigma^2\right)dt + \sigma\,dW_t.
$$
Integrating from $0$ to $T$ yields:
$$
S_T = S_0 \exp\!\left(\left(r - \tfrac12\sigma^2\right)T + \sigma\sqrt{T}\,Z\right),\quad Z\sim \mathcal{N}(0,1).
$$

### 4.3 Payoffs
- European call: $h(S_T)=(S_T-K)^+ = \max(S_T-K,0)$
- European put: $h(S_T)=(K-S_T)^+ = \max(K-S_T,0)$

### 4.4 Pricing equation (risk-neutral valuation)
$$
V_0 = e^{-rT}\,\mathbb{E}^{\mathbb{Q}}[h(S_T)].
$$

---

## 5. Numerical Methods Specification (Primary Track: Monte Carlo)

### 5.1 Basic Monte Carlo estimator
Define discounted payoff random variable:
$$
X = e^{-rT}h(S_T).
$$
With i.i.d. samples $Z_i\sim\mathcal{N}(0,1)$, compute $S_T^{(i)}$ and $X_i$, then:
$$
\widehat{V}_N = \frac{1}{N}\sum_{i=1}^N X_i.
$$

**Properties**
- Unbiased: $\mathbb{E}[\widehat{V}_N]=V_0$
- Variance: $\mathrm{Var}(\widehat{V}_N)=\mathrm{Var}(X)/N$
- CLT: $\sqrt{N}(\widehat{V}_N-V_0)\Rightarrow \mathcal{N}(0,\mathrm{Var}(X))$

### 5.2 Standard error and confidence interval
Estimate variance with sample variance:
$$
\widehat{\mathrm{Var}}(X)=\frac{1}{N-1}\sum_{i=1}^N (X_i-\overline{X})^2.
$$
Standard error of the mean:
$$
\mathrm{SE}(\widehat{V}_N)=\sqrt{\widehat{\mathrm{Var}}(X)/N}.
$$
Approximate 95% confidence interval:
$$
\widehat{V}_N \pm 1.96\,\mathrm{SE}(\widehat{V}_N).
$$

### 5.3 Variance reduction requirements

#### 5.3.1 Antithetic variates
For each $Z$, also use $-Z$. Define:
$$
\widehat{V}^{\text{anti}}_N=\frac{1}{N}\sum_{i=1}^N \frac{X(Z_i)+X(-Z_i)}{2}.
$$
**Expected outcome:** lower variance for monotone payoffs (calls/puts) due to negative correlation.

#### 5.3.2 Control variates (with known expectation)
Choose a control variable $Y$ correlated with $X$ and with known mean.
A standard choice:
$$
Y=e^{-rT}S_T,\qquad \mathbb{E}[Y]=S_0.
$$
Estimator:
$$
\widehat{V}^{\text{cv}}=\frac{1}{N}\sum_{i=1}^N \left(X_i - \beta (Y_i-\mathbb{E}[Y])\right).
$$
Optimal coefficient:
$$
\beta^*=\frac{\mathrm{Cov}(X,Y)}{\mathrm{Var}(Y)}.
$$
In practice estimate $\beta^*$ from samples.

**Acceptance criterion:** demonstrate variance reduction factor empirically, e.g.
$$
\frac{\widehat{\mathrm{Var}}(\widehat{V}_N)}{\widehat{\mathrm{Var}}(\widehat{V}^{\text{cv}}_N)} > 1.
$$

### 5.4 Greeks (pathwise derivative)
Let $V(S_0,\sigma,r,T)=e^{-rT}\mathbb{E}[h(S_T)]$.

#### 5.4.1 Delta
Since $S_T = S_0 \exp(\cdots)$, we have:
$$
\frac{\partial S_T}{\partial S_0}=\frac{S_T}{S_0}.
$$
For a call, $h'(S_T)=\mathbf{1}_{\{S_T>K\}}$ almost everywhere.
Thus:
$$
\Delta = \frac{\partial V}{\partial S_0}
= e^{-rT}\mathbb{E}\left[\mathbf{1}_{\{S_T>K\}}\frac{S_T}{S_0}\right].
$$
MC estimator:
$$
\widehat{\Delta}_N=\frac{e^{-rT}}{N}\sum_{i=1}^N \mathbf{1}_{\{S_T^{(i)}>K\}}\frac{S_T^{(i)}}{S_0}.
$$

#### 5.4.2 Vega
Differentiate:
$$
\log S_T = \log S_0 + (r-\tfrac12\sigma^2)T + \sigma\sqrt{T}Z.
$$
So:
$$
\frac{\partial \log S_T}{\partial \sigma} = -\sigma T + \sqrt{T}Z,
\qquad
\frac{\partial S_T}{\partial \sigma}=S_T(-\sigma T + \sqrt{T}Z).
$$
Hence for a call:
$$
\text{Vega} = e^{-rT}\mathbb{E}\left[\mathbf{1}_{\{S_T>K\}}\,S_T(-\sigma T+\sqrt{T}Z)\right].
$$

**Greeks acceptance criterion:** compare MC Greeks against analytic Greeks (Black–Scholes closed form) within statistical error.

---

## 6. Analytical Reference (Black–Scholes Closed-Form)

To validate MC, implement closed form pricing.

Define:
$$
d_1=\frac{\ln(S_0/K)+(r+\tfrac12\sigma^2)T}{\sigma\sqrt{T}},\quad
d_2=d_1-\sigma\sqrt{T}.
$$
Call:
$$
C = S_0\Phi(d_1) - K e^{-rT}\Phi(d_2).
$$
Put:
$$
P = K e^{-rT}\Phi(-d_2) - S_0\Phi(-d_1).
$$
Where $\Phi$ is standard normal CDF.

**Acceptance criterion:** MC estimates converge to analytic price; error decreases ~ $O(N^{-1/2})$.

---

## 7. Optional PDE Track (for CSE/Numerics Alignment)

### 7.1 Black–Scholes PDE
Option price $V(t,S)$ satisfies:
$$
\frac{\partial V}{\partial t}
+\frac12\sigma^2 S^2\frac{\partial^2 V}{\partial S^2}
+rS\frac{\partial V}{\partial S}
-rV=0,\quad V(T,S)=h(S).
$$

### 7.2 Weak form (Galerkin idea)
Choose test functions $w(S)$ and integrate over domain $S\in[S_{\min},S_{\max}]$ (truncation required).
A typical weak form after multiplying by $w$ and integrating (with integration by parts on the second derivative term) yields a bilinear form involving:
- mass term $\int V w \, dS$
- diffusion term $\int \sigma^2 S^2 V_S w_S \, dS$
- convection term $\int r S V_S w \, dS$
- reaction term $\int r V w \, dS$

Time discretization (e.g. backward Euler / Crank–Nicolson) gives linear systems per timestep.

**Why include this:** deterministic solver for 1D that lets you cross-check MC and show FEM competence.

---

## 8. Functional Requirements (FR)

### FR-1 Pricing API
Provide an API to compute:
- European call/put price under Black–Scholes
- methods: `MC`, `MC+anti`, `MC+cv`, `MC+anti+cv`
  Inputs:
- $S_0,K,r,\sigma,T$
- number of samples $N$
- RNG seed

Outputs:
- price estimate
- standard error
- confidence interval
- runtime metrics

### FR-2 Greeks API
Compute:
- Delta and Vega (at minimum)
  Outputs:
- estimate + standard error

### FR-3 Analytic reference
Compute closed-form Black–Scholes price and Greeks (Delta, Vega) for validation.

### FR-4 Experiment runner
CLI to run:
- convergence experiment over $N$ grid (e.g. 1e3…1e7)
- variance reduction comparison
- parameter sweeps over $K$, $\sigma$, $T$

### FR-5 Reproducibility
- Deterministic results under fixed seed
- Logs include git commit hash (optional), compiler flags, CPU info (optional), params

---

## 9. Non-Functional Requirements (NFR)

### NFR-1 Performance
- Baseline MC engine should handle $N \ge 10^7$ samples in reasonable time on VPS hardware (exact thresholds depend on CPU).
- Vectorization-friendly and allocation-free inner loop.

### NFR-2 Numerical correctness
- Pass regression tests comparing to analytic price within tolerance tied to SE:
    - e.g. $|\widehat{V}_N - V_{\text{BS}}| \le 3\,\mathrm{SE}$ for large $N$.

### NFR-3 Maintainability
- Clear module boundaries: model vs payoff vs engine vs stats.
- Minimal header coupling.
- Consistent naming, docs, and unit tests.

### NFR-4 Portability
- Build with CMake on Linux; optional macOS.
- No reliance on proprietary libraries.

---

## 10. System Architecture Requirements

### 10.1 C++ core modules
- `models/`
    - `black_scholes.hpp/.cpp`
- `payoffs/`
    - `payoff.hpp`
    - `call_payoff.hpp/.cpp`
    - `put_payoff.hpp/.cpp`
- `mc/`
    - `mc_engine.hpp` (templated or type-erased interface)
    - `variance_reduction.hpp` (anti/cv)
    - `stats.hpp` (mean, variance, CI)
- `analytics/`
    - `bs_closed_form.hpp/.cpp` (price + Greeks)
- `cli/`
    - `main.cpp` experiment runner

### 10.2 Python layer (optional)
- `experiments/`
    - `convergence.py`
    - `variance_reduction.py`
    - `plots.py`

Binding options:
- pybind11 wrapper around core functions OR
- run CLI and parse CSV output (simpler and still professional).

---

## 11. Step-by-Step Implementation Plan (What to implement, in order)

### Step 1 — Deterministic foundation (no variance reduction yet)
**Implement**
- Black–Scholes terminal sampler: `ST(Z)`
- Payoffs: call/put
- MC estimator: price
- Stats: mean, sample variance, SE, CI

**Verification**
- sanity: $S_T$ sample mean close to $S_0 e^{rT}$
- price monotonicity:
    - call increases with $S_0$, decreases with $K$
    - put decreases with $S_0$, increases with $K$

### Step 2 — Closed-form Black–Scholes
**Implement**
- $\Phi$ (normal CDF) using `std::erfc`/`std::erf`
- call/put analytic price
- analytic Delta/Vega (optional now, required later)

**Verification**
- compare MC price to analytic for increasing $N$
- show empirical $1/\sqrt{N}$ error trend on log-log plot (Python)

### Step 3 — Antithetic variates
**Implement**
- paired sampling: evaluate $Z$ and $-Z$ per iteration
- update stats on paired average payoff

**Verification**
- variance reduction factor > 1 for calls/puts

### Step 4 — Control variates
**Implement**
- compute $Y_i = e^{-rT}S_T^{(i)}$, with known mean $S_0$
- estimate $\beta^*$ via sample cov/var
- output both raw and CV prices + variances

**Verification**
- variance reduction factor consistent across parameters
- show dependence on correlation $\rho_{XY}$

### Step 5 — Greeks (pathwise)
**Implement**
- Delta estimator for call/put
- Vega estimator for call/put
- SE for Greeks (same sample variance approach)

**Verification**
- compare to analytic Greeks (Black–Scholes) within SE bands

### Step 6 — Performance engineering
**Implement**
- avoid per-iteration allocations
- optional OpenMP parallelization
- benchmark scaling with threads

**Verification**
- measure throughput paths/sec
- show speedup and parallel efficiency

### Step 7 (Optional) — PDE Solver (FD or FEM)
**Implement**
- domain truncation $S\in[S_{\min},S_{\max}]$
- boundary conditions (e.g. call: $V(t,0)=0$, $V(t,S_{\max})\approx S_{\max}-K e^{-r(T-t)}$)
- time stepping and spatial discretization (Galerkin/FEM or FD)

**Verification**
- PDE solution matches analytic at $t=0$
- compare PDE vs MC vs analytic

---

## 12. Testing Strategy

### 12.1 Unit tests (fast)
- `terminal_price(Z)` correctness for fixed Z
- payoff correctness at boundary cases
- normal CDF sanity checks

### 12.2 Numerical regression tests (slower)
- Fix seed and moderate N (e.g. 1e6) and verify price within tolerance window
- Verify CI covers analytic price most of the time (statistical test across runs)

### 12.3 Property tests (optional)
- invariants like put-call parity:
  $$
  C - P = S_0 - K e^{-rT}.
  $$
  Use analytic or MC estimates to test parity (MC will have noise).

---

## 13. Risk Register (What can go wrong)

- **RNG issues:** poor seeding or non-determinism in parallel runs.
- **Estimator bugs:** incorrect discounting, wrong variance formula, wrong control mean.
- **Numerical instability:** CDF implementation errors for extreme $d_1,d_2$.
- **Performance pitfalls:** unnecessary allocations, virtual dispatch in hot loop.
- **PDE truncation error:** wrong boundary conditions dominate solution.

Mitigation: keep a known parameter set where analytic results are stable; build regression tests early.

---

## 14. Acceptance Criteria (Definition of Done)

Baseline completion:
1. MC pricing returns price + SE + CI.
2. Analytic Black–Scholes price implemented.
3. Convergence plot shows MC error ~ $N^{-1/2}$.
4. Antithetic and control variate implemented with demonstrated variance reduction.
5. Delta and Vega implemented and validated vs analytic Greeks.
6. CLI runs experiments and outputs CSV/JSON for Python plotting.

Advanced completion (optional):
7. OpenMP scaling plot + efficiency.
8. PDE solver cross-checks analytic solution.
9. Python binding or orchestration layer produces publication-quality plots.

---

## 15. Implementation Notes (Engineering choices)

### 15.1 RNG
- Use `std::mt19937_64` + `std::normal_distribution<double>`
- For parallel runs: per-thread RNG with deterministic seed schedule.

### 15.2 Hot loop design
- Prefer templates or function objects to avoid virtual calls inside the MC loop.
- Keep payoff polymorphism at the boundary (setup), not inside the innermost loop.

### 15.3 Data output
- Output CSV with columns:
    - method, N, price, se, ci_low, ci_high, runtime_ms, seed, params...

This makes Python plotting trivial.

---

## 16. Suggested Reading Map (aligned with requirements)

- **Black–Scholes theory / derivations:** Shreve, *Stochastic Calculus for Finance II*
- **Monte Carlo + variance reduction + Greeks:** Glasserman, *Monte Carlo Methods in Financial Engineering*
- **C++ architecture for pricing libraries:** Joshi, *C++ Design Patterns and Derivatives Pricing*
- **PDE + FEM track:** any numerical PDE/FEM text; treat BS PDE as a parabolic convection–diffusion–reaction equation.

---

## Appendix A — Analytic Greeks (for validation)

### Call Delta
$$
\Delta_{\text{call}}=\Phi(d_1).
$$

### Put Delta
$$
\Delta_{\text{put}}=\Phi(d_1)-1.
$$

### Vega (call = put)
$$
\text{Vega}= S_0 \phi(d_1)\sqrt{T},
$$
where $\phi$ is standard normal PDF:
$$
\phi(x)=\frac{1}{\sqrt{2\pi}}e^{-x^2/2}.
$$

---

## Appendix B — Put-Call Parity
$$
C - P = S_0 - K e^{-rT}.
$$
Use this as an additional correctness check.

---