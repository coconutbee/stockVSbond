import pandas as pd, numpy as np
# 1. 讀取指數歷史價格
stocks = pd.read_csv('sp500.csv', index_col='Date', parse_dates=True)['Close']
bonds  = pd.read_csv('bonds.csv',  index_col='Date', parse_dates=True)['Close']
# 2. 計算報酬率
rtn_s = stocks.pct_change().dropna()
rtn_b = bonds.pct_change().dropna()
# 3. 回測不同配比
results = []
for w in np.arange(0, 1.01, 0.1):
    port = w * rtn_s + (1-w) * rtn_b
    ann_r = (1+port.mean())**12 - 1
    ann_vol = port.std() * np.sqrt(12)
    sharpe = ann_r / ann_vol
    results.append({'w_stock':w, 'ann_r':ann_r, 'ann_vol':ann_vol, 'Sharpe':sharpe})
df = pd.DataFrame(results)
# 4. 繪圖與表格
