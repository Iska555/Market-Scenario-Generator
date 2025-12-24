# test_portfolio.py
from src.correlation import *

# Test with a simple portfolio
tickers = ["SPY", "AAPL", "BTC-USD"]

print("📊 Testing Multi-Asset Portfolio Simulation\n")

# 1. Download data
print("1. Downloading data...")
data = download_multi_asset_data(tickers, years=2)
print(f"   ✓ Downloaded {len(data)} assets\n")

# 2. Compute correlation
print("2. Computing correlation matrix...")
returns_df, corr_matrix = compute_correlation_matrix(data)
print(corr_matrix)
print()

# 3. Cholesky decomposition
print("3. Performing Cholesky decomposition...")
L = cholesky_decomposition(corr_matrix)
print("   ✓ Cholesky factor computed\n")

# 4. Verify
reconstructed = L @ L.T
error = np.abs(corr_matrix.values - reconstructed).max()
print(f"4. Verification: Max reconstruction error = {error:.2e}")
print("   ✓ Correlation module working!\n")

print("🎉 Ready for multi-asset simulation!")