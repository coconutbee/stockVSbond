import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="Bond‐Stock 配置計算器", layout="wide")
st.title("20+年期公債、1~3年期公債 與 SPY 配置分析")

# 1. 檔案選擇
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
if not csv_files:
    st.error("目前目錄下沒有 .csv 檔，請先放入格式為 Date,Price,Dividend 的檔案")
    st.stop()

st.sidebar.header("🔸 選擇資料檔")
file_20plus = st.sidebar.selectbox("20+ 年期公債 CSV 檔", csv_files)
file_1to3   = st.sidebar.selectbox("1–3 年期公債 CSV 檔", csv_files)
file_spy    = st.sidebar.selectbox("SPY 大盤股票 CSV 檔", csv_files)

# 2. 配置比例設定
st.sidebar.header("🔹 設定資產配置比例 (總和需=1)")
w_20   = st.sidebar.slider("20+ 年期公債",   0.0, 1.0, 0.33, step=0.01)
w_1to3 = st.sidebar.slider("1–3 年期公債",   0.0, 1.0, 0.33, step=0.01)
w_spy  = st.sidebar.slider("SPY 大盤股票", 0.0, 1.0, 0.34, step=0.01)
if abs((w_20 + w_1to3 + w_spy) - 1.0) > 1e-6:
    st.sidebar.error("❗ 配置比例總和不等於 1，請調整")
    st.stop()

@st.cache_data
def load_returns(path):
    df = pd.read_csv(path, parse_dates=['Date'])
    df = df.sort_values('Date')
    df['Price'] = pd.to_numeric(
        df['Price'].astype(str).str.replace("'", "").str.replace(",", ""),
        errors='coerce'
    )
    df['Dividend'] = pd.to_numeric(df['Dividend'], errors='coerce').fillna(0.0)
    df['Return'] = (df['Price'] + df['Dividend']) / df['Price'].shift(1) - 1
    return df[['Date','Return']].dropna()

# 3. 計算各資產日報酬
df20  = load_returns(file_20plus).rename(columns={'Return':'Ret20'})
df13  = load_returns(file_1to3)  .rename(columns={'Return':'Ret1to3'})
dfspy = load_returns(file_spy)   .rename(columns={'Return':'RetSPY'})

# 4. 合併
df = df20.merge(df13, on='Date', how='inner').merge(dfspy, on='Date', how='inner')

# 5. 計算投組日報酬、累積報酬
weights = np.array([w_20, w_1to3, w_spy])
rets_mat = df[['Ret20','Ret1to3','RetSPY']].to_numpy().T
df['PortRet'] = weights.dot(rets_mat)
df['Cumulative Return'] = (1 + df['PortRet']).cumprod() - 1

# 6. 全期績效指標
ann_ret = (1 + df['PortRet'].mean())**252 - 1
ann_vol = df['PortRet'].std() * np.sqrt(252)
sharpe  = ann_ret / ann_vol if ann_vol > 0 else np.nan

st.subheader("📊 全期績效指標")
c1, c2, c3 = st.columns(3)
c1.metric("年度化平均報酬率", f"{ann_ret*100:.2f}%")
c2.metric("年度化波動度",     f"{ann_vol*100:.2f}%")
c3.metric("夏普比率",         f"{sharpe:.2f}")

# 7. 每年年化報酬率與年末累積報酬
df['Year'] = df['Date'].dt.year
annual_list = []
for year, grp in df.groupby('Year'):
    # 該年度天數
    n = len(grp)
    # 該年度總報酬
    yearly_ret = (1 + grp['PortRet']).prod() - 1
    # 年化報酬率
    ann_y = (1 + yearly_ret)**(252/n) - 1
    # 年末累積報酬（從起始日算到該年年度末）
    cum_end = grp['Cumulative Return'].iloc[-1]
    annual_list.append({
        'Year': year,
        '年化報酬率': ann_y,
        '年末累積報酬': cum_end
    })
annual_df = pd.DataFrame(annual_list).set_index('Year')

st.subheader("📅 每年績效一覽")
st.dataframe(
    annual_df.style.format({
        '年化報酬率': '{:.2%}',
        '年末累積報酬': '{:.2%}'
    })
)

# 8. 顯示累積報酬時間序列
st.subheader("📈 累積報酬走勢")
st.line_chart(df.set_index('Date')[['Cumulative Return']])
