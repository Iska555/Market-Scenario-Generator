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
    returns_preprocess.py     # Compute log returns & validate input
    generative_model.py       # Gaussian model (Day 2)
    gmm_model.py              # Gaussian Mixture Model (Day 3)
    visualization.py          # Historical/paths/distribution plots (Day 4)
    simulate_paths.py         # Unified scenario runner + visualization (Day 4)
    debug_day1.py             # Price & returns diagnostic tool (Day 1)

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

## Day 1 — Data Pipeline Foundation
- Implemented reliable data ingestion (`data_download.py`)
- Log return computation and validation (`returns_preprocess.py`)
- Diagnostic price/returns visualization (`debug_day1.py`)

## Day 2 — Gaussian Simulation Engine
- Baseline Normal return model  
- Price path construction  
- VaR/CVaR and volatility metrics  
- First simulation pipeline

## Day 3 — Gaussian Mixture Models (GMM)
- Added multi-regime fat-tailed return modeling  
- Support for 3-component mixture  
- Unified API: `run_scenario(..., model="gmm")`

## Day 4 — Visualization & Unified Runner
- Added plotting module (`visualization.py`)  
- Historical prices, simulated paths, final return histograms  
- Integrated risk statistics  
- Unified scenario runner supporting Gaussian and GMM

## Day 5 — EWMA Volatility Forecasting
Day 5 introduces a dynamic volatility model using RiskMetrics-style EWMA:

- `compute_ewma_vol` — backward-looking volatility estimator  
- `forecast_ewma_vol` — smooth forward volatility curve  
- `sample_ewma_returns` — Monte Carlo returns using time-varying σ(t)  
- `run_scenario(..., model="ewma")` now fully supported  
- Visualization updated to display EWMA volatility curves

EWMA simulations produce smoother, volatility-aware forward paths and more realistic risk metrics than constant-volatility Gaussian models.

---

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

