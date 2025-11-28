📈 Market Scenario Generator

A modular pipeline for financial time-series retrieval, preprocessing, and scenario simulation.

<div align="center">

</div>
🌐 Project Overview

The Market Scenario Generator is a quantitative finance project designed to build a robust workflow for:

📥 Downloading financial market data

🧹 Preprocessing price series

📊 Computing log returns

🔮 (Future) Generating realistic market scenarios for risk and portfolio analysis

The project will evolve over 9–10 days, with daily commits reflecting incremental development and debugging.

🚀 Current Progress (Day 1)
🗂️ 1. Data Acquisition Module — data_download.py

Responsible for collecting daily historical prices using yfinance.

Features:

📅 Adjustable lookback window (e.g., 1–5 years)

🔧 Handles missing data + ensures clean indexing

📊 Outputs a tidy DataFrame with:

index = date

column = price

🔄 Works with both adjusted and raw close prices

<div align="center">

</div>
🐞 2. Debugging & Verification — Day 1

Today’s debugging focused on ensuring reproducibility and code consistency:

🧩 Fixed mismatched function names (download_price_history → download_price_data)

🔍 Solved Series / DataFrame inconsistencies

🧼 Removed duplicate code and redundant transformations

⚠️ Added cleaner exception handling

This establishes a strong foundation before expanding the system.

📉 3. Returns Preprocessing — returns_preprocess.py

Handles the computation and attachment of log returns.

✔ Log return computation:
𝑟
𝑡
=
ln
⁡
(
𝑃
𝑡
)
−
ln
⁡
(
𝑃
𝑡
−
1
)
r
t
	​

=ln(P
t
	​

)−ln(P
t−1
	​

)
✔ Module features:

📐 Clean mathematical transformations

🧪 Input structure validation

💾 Output as a labeled Series (log_return)

🔗 Optional version that attaches returns back into the price DataFrame

<div align="center">

</div>
🛠️ Planned Development Over the Next 9–10 Days
Day	Goal
2	Return distributions, histograms, diagnostics
3	Scenario generation engine (bootstrap, random sampling)
4	Basic Monte Carlo simulations
5	Volatility modeling (EWMA)
6	Multi-asset support
7	Visualization suite
8	Backtesting helpers
9	Documentation + cleanup
10	Release v1.0
🗃️ Repository Structure
market-scenario-generator/
│
├── README.md          <- You're reading this!
├── .gitignore
├── src/
│   ├── data_download.py
│   ├── returns_preprocess.py
│   └── ...
└── ...
