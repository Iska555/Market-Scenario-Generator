# Market Scenario Generator

This repository contains the foundation of a financial simulation and risk analysis engine.  
The goal is to generate synthetic future return paths for market assets and compute risk metrics such as VaR, CVaR, volatility, and probability of loss.

The project focuses on building a modular, extensible pipeline for scenario generation, return modeling, and simulation-based risk evaluation.  
Upcoming stages will include advanced distribution modeling, volatility forecasting, multi-asset simulation, and a public-facing UI.

---

# 📘 Project Motivation

Risk management relies on understanding possible future market paths rather than predicting a single outcome.  
Scenario generation is used in:

- portfolio stress testing  
- Value-at-Risk (VaR) calculations  
- capital planning  
- quantitative research  
- algorithmic strategy evaluation  

This project builds a clean, flexible framework for generating thousands of plausible market paths using historical data and statistical models.

The long-term goal is to support:

- Gaussian return models  
- fat-tailed models  
- Gaussian mixtures  
- VAEs for generative modeling  
- GARCH-style volatility dynamics  
- bootstrap and block bootstrap sampling  
- multi-asset simulation  
- web-based visualization and API endpoints  

---

# 📂 Repository Structure

```
src/
    data_download.py          # Download historical prices
    returns_preprocess.py     # Compute log returns + validation
    generative_model.py       # Gaussian model fitting and sampling (Day 2)
    simulate_paths.py         # Full Gaussian simulation pipeline (Day 2)
    debug_day1.py             # Data and returns visualization tool

requirements.txt
.gitignore
README.md
```

---

# 🧩 Methodology Overview

The project is organized into sequential modules:

### 1. Data Acquisition
- Download daily market prices  
- Clean and standardize the series  
- Provide a consistent foundation for return modeling  

### 2. Return Transformation
- Convert raw prices into daily log returns  
- Validate clean numerical outputs  
- Prepare inputs for distribution fitting and sampling  

### 3. Generative Modeling
- Fit statistical models to return distributions  
- Sample synthetic returns  
- Build multi-day forward paths  

(Current: Gaussian baseline model)

### 4. Risk Evaluation
- Convert simulated returns to price paths  
- Compute risk metrics: mean, volatility, VaR, CVaR  
- Generate diagnostic visualizations  

---

# 🖥️ Running the Project

### Install dependencies
```
pip install -r requirements.txt
```

### Run Day 1 validation
```
python -m src.debug_day1
```
Outputs:
- price history  
- log return histogram  

### Run Day 2 simulation
```
python -m src.simulate_paths
```
Outputs:
- simulated price trajectories  
- printed risk statistics  

---

# 📈 Project Progress

Below are detailed summaries of Day 1 and Day 2.

---

# Day 1 — Data Pipeline Foundation

## 1. Data Acquisition Module — `data_download.py`

Implements a consistent interface for downloading daily historical prices.

Features:

- Automatic download using `yfinance`  
- Adjustable time window (e.g., last 3 years)  
- Support for adjusted or raw closing prices  
- Standardized output as a DataFrame with:
  - date index  
  - single `price` column  

Provides clean, validated data for all downstream steps.

---

## 2. Return Preprocessing — `returns_preprocess.py`

Handles return computation and input validation.

Includes:

### Log Return Calculation
```
r_t = ln(P_t) - ln(P_{t-1})
```

### Data Validation
- checks for missing price column  
- enforces float types  
- removes NaNs created by differencing  

### Pipeline Options
- standalone return function  
- DataFrame augmentation function  

---

## 3. Debug Visualization — `debug_day1.py`

Used to verify correctness of the Day 1 pipeline.

Running the script generates:
- a price chart  
- a histogram of daily log returns  

Confirms correct data ingestion and preprocessing.

---

# Day 2 — Gaussian Simulation Engine

Day 2 adds the first complete scenario-generation pipeline.

## 1. Generative Model — `generative_model.py`

Implements the baseline Normal return model.

### fit_gaussian(returns)
- calculates mean and standard deviation  
- handles NaNs  
- produces clean parameters for sampling  

### sample_gaussian(mu, sigma, horizon, num_paths)
- generates synthetic daily log returns from N(μ, σ²)  
- output: `(num_paths, horizon)`  

This establishes the baseline scenario model.

---

## 2. Simulation Pipeline — `simulate_paths.py`

Builds the full simulation workflow.

### Workflow Steps:

#### 1. Data Retrieval  
- download price history  
- compute daily log returns  

#### 2. Model Fitting  
- estimate μ and σ  

#### 3. Scenario Generation  
- sample future log returns  

#### 4. Price Path Construction  
```
P_t = P_0 * exp(cumulative_log_returns)
```

#### 5. Risk Metrics Computation
- mean  
- volatility  
- VaR 95  
- CVaR 95  
- probability of loss  

#### 6. Visualization in Test Mode
- plots first 30 simulated price paths  

Confirms that the Gaussian engine works correctly.

---
# Day 3 — Gaussian Mixture Models (GMM)

Day 3 introduces the first non-Gaussian scenario model.  
A Gaussian Mixture Model improves realism by capturing fat tails and multiple market regimes.

## 1. GMM Module — `gmm_model.py`

This module implements the statistical mixture model for log returns.

### Capabilities:
- Fit a K-component Gaussian Mixture (default: 3)
- Estimate component-level:
  - means  
  - volatilities  
  - mixture weights  
- Sample synthetic returns from the fitted mixture distribution

The GMM captures volatility shifts, heavy tails, and multi-modal distributions.

---

## 2. Unified Scenario API — `run_scenario`

The simulation pipeline now supports:
- Gaussian model  
- Gaussian Mixture Model  

The API interface:

```python
run_scenario(
    ticker="SPY",
    years=3,
    horizon=252,
    num_paths=1000,
    model="gmm"
)
```

This design supports future models such as:
- fat-tailed distributions
- t-distributions
- VAE-based generators
- bootstrap models
- regime-switching models

---

## 3. Output Behavior

GMM produces paths with:
- higher kurtosis  
- more realistic downside risk  
- improved VaR and CVaR accuracy  

Visual inspection confirms heavier tails compared to Gaussian-only results.

Day 3 establishes the foundation for advanced return modeling and prepares the project for volatility modeling in upcoming development days.

# Day 4 — Visualization Layer & Unified Scenario Runner

Day 4 introduces a complete visualization system and a unified scenario-execution pipeline.  
This addition transforms the project from a backend simulation engine into a research-ready analytical toolkit capable of producing clear diagnostic plots and structured risk outputs.

---

## 1. Unified Scenario Execution — `run_scenario`

A consolidated API now manages the entire simulation workflow:

- downloading historical prices  
- computing log returns  
- selecting and fitting a return model (Gaussian or GMM)  
- sampling synthetic future returns  
- building price paths  
- computing final returns  
- deriving risk metrics  

Example usage:

```python
df, paths, final_returns, stats = run_scenario(
    ticker="SPY",
    years=3,
    horizon=252,
    num_paths=1000,
    model="gmm"
)
```

This structure ensures reproducibility and modularity, making it easy to incorporate new models (t-distribution, bootstrap, VAE, GARCH) in later development phases.

---

## 2. Visualization Module — `visualization.py`

A dedicated visualization layer has been added to standardize how simulation results are displayed.  
The module provides three core plots:

### Historical Price Chart
Visualizes the input price series for the selected ticker.

```python
plot_historical_price(df, ticker)
```

### Simulated Scenario Paths
Shows a subset of simulated price trajectories to illustrate dispersion.

```python
plot_simulated_paths(paths, model)
```

### Final Return Distribution
Plots the distribution of ending returns and overlays VaR/CVaR thresholds.

```python
plot_final_return_distribution(final_returns, stats, model)
```

These plots form the visual backbone for scenario diagnostics, model comparison, and risk assessment.

---

## 3. Integrated Risk Statistics

Day 4 incorporates a set of standard risk metrics directly into the simulation pipeline:

- **mean return**  
- **volatility (standard deviation)**  
- **Value-at-Risk (VaR 95%)**  
- **Conditional VaR (CVaR 95%)**  
- **probability of loss**  

These statistics provide a concise summary of simulated tail risk and are computed from the full distribution of simulated final returns.

---

## 4. End-to-End Execution (Main Script)

The `simulate_paths.py` script now supports complete end-to-end execution.  
Running:

```
python -m src.simulate_paths
```

produces:

- historical price plot  
- simulated scenario paths  
- final return distribution  
- printed risk statistics  

This enables immediate visual and quantitative evaluation of model behavior and simulation accuracy.

---

## Day 4 Summary

Day 4 establishes the core analytical visualization and execution framework for the project:

- ✔ unified scenario API  
- ✔ Gaussian and GMM model support  
- ✔ complete plotting layer (historical, simulated paths, final distribution)  
- ✔ integrated tail-risk metrics  
- ✔ reproducible end-to-end workflow  

These additions prepare the system for a user-facing interface in Day 5 and for advanced generative and volatility models in later stages.


# 🔮 Future Extensions

The project will continue to evolve into a full-featured risk simulation system.  
Planned additions include:

- Enhanced GMM tuning and diagnostics  
- Block bootstrap and regime-aware bootstrap sampling  
- Fat-tailed and skewed distribution models  
- Variational Autoencoder (VAE) generative return models  
- EWMA and GARCH-style volatility structures  
- Multi-asset correlation modeling  
- Full Monte Carlo framework with scenario sets  
- REST API (FastAPI) and a dedicated front-end (Next.js)  
- Visualization dashboards for scenario analysis  

These modules will be added progressively across upcoming development days.

