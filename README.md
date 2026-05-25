# 📈 Stochastic Market Simulator

[![Live Demo](https://img.shields.io/badge/demo-online-green.svg)](https://stochastic-market-simulator.vercel.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-%5E18.0-61DAFB.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)

---

## 📖 Overview

The **Stochastic Market Simulator** is a full-stack finance application designed to simulate future market paths using advanced statistical models. Moving beyond simple random walks, this engine incorporates **Gaussian Mixture Models (GMM)** for "fat tail" risks and **Cholesky Decomposition** to model realistic correlations between multiple assets.

This project serves as a modular framework for portfolio stress testing, Value-at-Risk (VaR) calculation, and quantitative research.

---

## 🚀 Key Features

* **Multi-Asset Portfolio Simulation**: Construct portfolios with custom weights (e.g., "33% SPY, 33% BTC, 34% TSLA") and simulate their combined performance.
* **Correlation Modeling**: Uses **Cholesky Decomposition** to preserve the historical correlation structure between assets, ensuring that if assets typically move together, they do so in the simulation.
* **Advanced Statistical Models**:
    * **Gaussian Mixture Models (GMM)**: Captures multi-regime market behavior (e.g., bull vs. bear markets) and extreme outlier risks.
    * **EWMA Volatility**: Models time-varying volatility clusters (RiskMetrics style).
    * **Gaussian Baseline**: Standard random walk for comparison.
* **Probabilistic Forecasting**: Visualizes "Extreme Scenarios" (Best Case, Bullish, Median, Bearish, Worst Case) to highlight the asymmetry of risk.
* **Risk Analytics**: Automatically computes **VaR (95%)**, **CVaR (Expected Shortfall)**, Sharpe Ratio, and Probability of Loss.
* **Interactive Dashboard**: A modern React-based UI with Dark/Light mode support, interactive Recharts visualizations, and real-time portfolio configuration.

---

## 🛠️ Project Structure

The codebase is split into a Python backend API and a React frontend.

```bash
MARKET_SCENARIO_GENERATOR/
├── backend/                 # Python (FastAPI) Simulation Engine
│   ├── src/
│   │   ├── correlation.py   # Multi-asset Cholesky logic
│   │   ├── data_download.py # YFinance data ingestion
│   │   ├── gmm_model.py     # Gaussian Mixture Logic
│   │   ├── ewma_vol.py      # Volatility forecasting
│   │   ├── generative_model.py # Core simulation logic
│   │   └── main.py          # FastAPI endpoints
│   └── requirements.txt
├── frontend/                # React (Vite + Tailwind) User Interface
│   ├── src/
│   │   ├── components/      # Recharts visualizations & Dashboards
│   │   ├── services/        # API connection logic
│   │   └── App.jsx          # Main application layout
│   └── package.json
---
```

## ⚡ Quick Start

### 1. Backend Setup (Python)

Navigate to the backend folder and start the API server.
bash cd backend python -m venv env # Activate: .\env\Scripts\activate (Windows) or source env/bin/activate (Mac/Linux) pip install -r requirements.txt # Run the API Server uvicorn main:app --reload --reload-exclude "env"
*The API will run at `http://localhost:8000*`

### 2. Frontend Setup (React)

Open a new terminal and launch the dashboard.

**Note:** If running locally, ensure `API_URL` in `App.jsx` is set to `http://localhost:8000`.
bash cd frontend npm install npm run dev
*The UI will launch at `http://localhost:5173*`

---

## ☁️ Deployment Architecture

This project is deployed using a decoupled microservices architecture:

* **Frontend**: Deployed on **Vercel** (Static React App).
* **Backend**: Deployed on **Render** (Python Web Service).
* **Data**: Fetches live market data via `yfinance` dynamically on every simulation request.

---

## 🧩 Methodology & Models

### Data Pipeline

1. **Ingestion**: Fetches daily adjusted close prices via `yfinance`.
2. **Preprocessing**: Computes Log Returns `ln(Pt / Pt-1)` to ensure stationarity.

### Simulation Models

| Model | Description | Best For |
| --- | --- | --- |
| **Gaussian (Normal)** | Assumes returns follow a bell curve with constant volatility. | Simple, stable baselines. |
| **GMM (Fat-Tailed)** | Fits multiple Gaussian distributions to capture extreme events (tails). | **Realistic stress testing** and crash simulation. |
| **EWMA Volatility** | Recursively weights recent data more heavily (Lambda = 0.94). | Short-term volatility forecasting. |
| **Cholesky (Multi-Asset)** | Decomposes the Covariance Matrix (Σ) to generate correlated random shocks. | **Portfolio Diversification Analysis**. |

### Risk Metrics

* **VaR (Value at Risk)**: The maximum loss expected with 95% confidence.
* **CVaR (Conditional VaR)**: The average loss *given* that the loss exceeds the VaR (tail risk).
* **Sharpe Ratio**: Risk-adjusted return metric (`Return / Volatility`).

---

## 🔮 Roadmap

* [x] **Phase 1**: Data Pipeline & Gaussian Models
* [x] **Phase 2**: Advanced GMM & Fat-Tail Modeling
* [x] **Phase 3**: React UI & Interactive Visualization
* [x] **Phase 4**: Multi-Asset Correlation (Cholesky Decomposition)
* [x] **Phase 5**: Portfolio-Level Simulation, Median Returns & Allocation UI
* [ ] **Phase 6**: GARCH(1,1) Volatility Models

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any new features or bug fixes.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.