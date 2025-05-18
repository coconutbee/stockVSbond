import streamlit as st
import pandas as pd
import numpy as np
import os
import altair as alt

st.set_page_config(page_title="Bond-Stock 配置計算器", layout="wide")
st.title("20+年期公債、1~3年期公債 與 SPY 配置分析")

# 找出所有 CSV 檔
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
if not csv_files:
    st.error("目前目錄下沒有 .csv 檔，請先放入至少三個格式為 Date, Price, Dividend 的檔案")
    st.stop()

# 1️⃣ 選檔
st.sidebar.header("1️⃣ 選擇 CSV 檔案")
file_20plus = st.sidebar.selectbox("20年以上公債", csv_files, index=0)
file_1to3   = st.sidebar.selectbox("1~3年期公債", csv_files, index=1 if len(csv_files)>1 else 0)
file_spy    = st.sidebar.selectbox("SPY 大盤股票", csv_files, index=2 if len(csv_files)>2 else 0)

# 2️⃣ 配置比例
st.sidebar.header("2️⃣ 調整資產配置 (總和必須=1)")
split1, split2 = st.sidebar.slider(
    "拖動兩端以設定分界點", 0.0, 1.0, (0.33, 0.66), 0.01
)
w_20   = split1
w_1to3 = split2 - split1
w_spy  = 1 - split2
if min(w_20, w_1to3, w_spy) < 0:
    st.sidebar.error("❗ 請確保分界點順序正確")
    st.stop()

# 讀 CSV 並計算日報酬的函式
@st.cache_data
def load_returns(path):
    df = pd.read_csv(path, parse_dates=['Date']).sort_values('Date')
    df['Price'] = pd.to_numeric(df['Price'].astype(str)
                                .str.replace("'", "").str.replace(",", ""),
                                errors='coerce')
    df['Dividend'] = pd.to_numeric(df['Dividend'], errors='coerce').fillna(0.0)
    df['Return'] = (df['Price'] + df['Dividend']) / df['Price'].shift(1) - 1
    return df[['Date','Return']].dropna()

# 先載入三檔的 df，並取各自最小/最大日期
df20  = load_returns(file_20plus).rename(columns={'Return':'Ret20'})
df13  = load_returns(file_1to3)  .rename(columns={'Return':'Ret1to3'})
dfspy = load_returns(file_spy)   .rename(columns={'Return':'RetSPY'})

# 3️⃣ 回测期起訖（直接從 df20/df13/dfspy 拿）
min_d = min(df20['Date'].min(), df13['Date'].min(), dfspy['Date'].min()).date()
max_d = max(df20['Date'].max(), df13['Date'].max(), dfspy['Date'].max()).date()
start_date, end_date = st.sidebar.date_input(
    "3️⃣ 選擇回測期間",
    (min_d, max_d),
    min_value=min_d,
    max_value=max_d
)

# 其餘計算合併、投組報酬、累積報酬…
df = df20.merge(df13, on='Date').merge(dfspy, on='Date')
weights = np.array([w_20, w_1to3, w_spy])
rets = df[['Ret20','Ret1to3','RetSPY']].to_numpy().T
df['PortRet'] = weights.dot(rets)
df['Cumulative Return'] = (1 + df['PortRet']).cumprod() - 1

# 根據選定期間過濾
mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
df_f = df[mask]

# 顯示績效
ann_ret = (1 + df_f['PortRet'].mean())**252 - 1
ann_vol = df_f['PortRet'].std() * np.sqrt(252)
sharpe  = ann_ret/ann_vol if ann_vol else np.nan
st.subheader("📊 績效指標")
c1, c2, c3 = st.columns(3)
c1.metric("年化報酬率", f"{ann_ret:.2%}")
c2.metric("年化波動度", f"{ann_vol:.2%}")
c3.metric("夏普比率",   f"{sharpe:.2f}")

# 累積報酬走勢
st.subheader("📈 累積報酬走勢")
st.line_chart(df_f.set_index('Date')['Cumulative Return'])
