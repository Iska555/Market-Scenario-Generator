# 📈 Market Scenario Generator

**An advanced financial simulation and risk analysis engine capable of modeling fat-tailed return distributions and generating volatility-aware synthetic market scenarios.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-%5E19.0-61DAFB.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)

---

## 📖 Overview

The **Market Scenario Generator** is a full-stack finance application designed to simulate future market paths using advanced statistical models. Unlike traditional tools that rely on simple normal distributions, this engine incorporates **Gaussian Mixture Models (GMM)** and **EWMA Volatility** to capture "fat tails" and realistic market crashes.

This project serves as a modular framework for portfolio stress testing, Value-at-Risk (VaR) calculation, and quantitative research.

---

## 🚀 Key Features

* **Monte Carlo Simulation**: Generate thousands of plausible future price paths for any US equity (S&P 500, AAPL, etc.).
* **Advanced Modeling**:
    * **Gaussian Mixture Models (GMM)**: Captures multi-regime market behavior (e.g., bull vs. bear markets) and fat-tailed risks.
    * **EWMA Volatility**: Models time-varying volatility clusters (RiskMetrics style).
    * **Gaussian Baseline**: Standard random walk for comparison.
* **Risk Analytics**: Automatically computes **VaR (95%)**, **CVaR (Expected Shortfall)**, Volatility, and Probability of Loss.
* **Interactive Dashboard**: A modern React-based UI to configure simulations and visualize complex return distributions in real-time.

---

## 🛠️ Project Structure

The codebase is split into a Python backend API and a React frontend.

```bash
MARKET_SCENARIO_GENERATOR/
├── backend/               # Python (FastAPI) Simulation Engine
│   ├── env/               # Virtual Environment
│   ├── src/
│   │   ├── data_download.py       # YFinance data ingestion
│   │   ├── gmm_model.py           # Gaussian Mixture Logic
│   │   ├── ewma_vol.py            # Volatility forecasting
│   │   ├── generative_model.py    # Core simulation logic
│   │   ├── simulate_paths.py      # Unified scenario runner
│   │   └── main.py                # FastAPI endpoints
│   └── requirements.txt
│
├── frontend/              # React (Vite + Tailwind) User Interface
│   ├── src/
│   │   ├── components/    # Recharts visualizations & Dashboards
│   │   ├── services/      # API connection logic
│   │   └── App.jsx        # Main application layout
│   └── package.json

-----

## ⚡ Quick Start

### 1\. Backend Setup (Python)

Navigate to the backend folder and start the API server.
bash cd backend python -m venv env # Activate: .\env\Scripts\activate (Windows) or source env/bin/activate (Mac/Linux) pip install -r requirements.txt # Run the API Server (Reloads on code changes, ignores env folder) uvicorn main:app --reload --reload-exclude "env"
*The API will run at `http://localhost:8000`*

### 2\. Frontend Setup (React)

Open a new terminal and launch the dashboard.
bash cd frontend npm install npm run dev
*The UI will launch at `http://localhost:5173`*

-----

## 🧩 Methodology & Models

### Data Pipeline

1.  **Ingestion**: Fetches daily adjusted close prices via `yfinance`.
2.  **Preprocessing**: Computes Log Returns ($r_t = \ln(P_t / P_{t-1})$) to ensure stationarity.

### Simulation Models

| Model | Description | Best For |
| :--- | :--- | :--- |
| **Gaussian (Normal)** | Assumes returns follow a bell curve with constant volatility. | Simple, stable baselines. |
| **GMM (Fat-Tailed)** | Fits multiple Gaussian distributions to capture extreme events (tails). | **Realistic stress testing** and crash simulation. |
| **EWMA Volatility** | Recursively weights recent data more heavily ($\sigma_t^2 = \lambda \sigma_{t-1}^2 + (1-\lambda)r_{t-1}^2$). | Short-term volatility forecasting. |

### Risk Metrics

  * **VaR (Value at Risk)**: The maximum loss expected with 95% confidence.
  * **CVaR (Conditional VaR)**: The average loss *given* that the loss exceeds the VaR (tail risk).

-----

## 🔮 Roadmap

  * [x] **Phase 1**: Data Pipeline & Gaussian Models
  * [x] **Phase 2**: Advanced GMM & Fat-Tail Modeling
  * [x] **Phase 3**: React UI & Interactive Visualization
  * [ ] **Phase 4**: Multi-Asset Correlation (Cholesky Decomposition)
  * [ ] **Phase 5**: GARCH(1,1) Volatility Models
  * [ ] **Phase 6**: Portfolio-Level Simulation

-----

## 🤝 Contributing

Contributions are welcome\! Please fork the repository and submit a pull request for any new features or bug fixes.

-----

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.