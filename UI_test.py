import streamlit as st
import pandas as pd
import numpy as np
import os
import altair as alt  # 新增 Altair

st.set_page_config(page_title="Bond‐Stock 配置計算器", layout="wide")
st.title("20+年期公債、1~3年期公債 與 SPY 配置分析")

# 找出所有 CSV 檔
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
if not csv_files:
    st.error("目前目錄下沒有 .csv 檔，請先放入至少三個格式為 Date, Price, Dividend 的檔案")
    st.stop()

# Sidebar：選擇三類資產的檔案
st.sidebar.header("1️⃣ 選擇 CSV 檔案")
file_20plus = st.sidebar.selectbox("20年以上公債 CSV 檔", csv_files, index=0)
file_1to3   = st.sidebar.selectbox("1~3年期公債 CSV 檔", csv_files, index=1 if len(csv_files)>1 else 0)
file_spy    = st.sidebar.selectbox("SPY 大盤股票 CSV 檔", csv_files, index=2 if len(csv_files)>2 else 0)

# Sidebar：調整三資產配置比例（用單條 Range Slider 產生兩個分割點）
st.sidebar.header("2️⃣ 調整資產配置 (總和必須=1)")
# 這裡用 range slider，value=(分點1, 分點2)，分別對應 20+、1~3、SPY 三段
split1, split2 = st.sidebar.slider(
    "拖動兩端以設定資產間的分界點",
    0.0, 1.0, value=(0.33, 0.66), step=0.01
)
# 依照分割點計算三種資產的比例
w_20   = split1
w_1to3 = split2 - split1
w_spy  = 1.0 - split2

# 防呆：三段比例應>=0
if min(w_20, w_1to3, w_spy) < 0:
    st.sidebar.error("❗ 請確保分割點順序正確，使三段比例均為正值")
    st.stop()

# 在 sidebar 顯示顏色分段條與百分比
st.sidebar.subheader("🔸 資產配置分布")
# 在 sidebar 顯示分段條形圖，並在每一段上方顯示百分比
segments = pd.DataFrame([
    {"Asset": "20年以上公債", "start": 0.0,             "end": w_20,              "Allocation": w_20},
    {"Asset": "1~3年期公債", "start": w_20,            "end": w_20 + w_1to3,     "Allocation": w_1to3},
    {"Asset": "SPY 大盤股票","start": w_20 + w_1to3,   "end": 1.0,                "Allocation": w_spy}
])

base = alt.Chart(segments).encode(
    x=alt.X('start:Q', axis=None, scale=alt.Scale(domain=[0,1])),
    x2='end:Q',
    color=alt.Color('Asset:N', legend=None)
)

bars = base.mark_bar(size=20)

labels = base.mark_text(
    align='center',
    dy=3  # 往上偏移文字
).transform_calculate(
    mid='(datum.start + datum.end) / 2'
).encode(
    x=alt.X('mid:Q'),
    text=alt.Text('Allocation:Q', format='.0%')
)

st.sidebar.altair_chart((bars + labels).properties(height=80), use_container_width=True)

# 接下來載入資料、計算日報酬、累積報酬等（不變）
@st.cache_data
def load_returns(path):
    df = pd.read_csv(path, parse_dates=['Date']).sort_values('Date')
    df['Price'] = pd.to_numeric(df['Price'].astype(str)
                                .str.replace("'", "")
                                .str.replace(",", ""), errors='coerce')
    df['Dividend'] = pd.to_numeric(df['Dividend'], errors='coerce').fillna(0.0)
    df['Return'] = (df['Price'] + df['Dividend']) / df['Price'].shift(1) - 1
    return df[['Date','Return']].dropna()

df20  = load_returns(file_20plus).rename(columns={'Return':'Ret20'})
df13  = load_returns(file_1to3)  .rename(columns={'Return':'Ret1to3'})
dfspy = load_returns(file_spy)   .rename(columns={'Return':'RetSPY'})

df = df20.merge(df13, on='Date', how='inner')\
         .merge(dfspy, on='Date', how='inner')

weights = np.array([w_20, w_1to3, w_spy])
rets_mat = df[['Ret20','Ret1to3','RetSPY']].to_numpy().T
df['PortRet'] = weights.dot(rets_mat)
df['Cumulative Return'] = (1 + df['PortRet']).cumprod() - 1

# 顯示績效指標與累積報酬走勢（同之前）
ann_ret = (1 + df['PortRet'].mean())**252 - 1
ann_vol = df['PortRet'].std() * np.sqrt(252)
sharpe  = ann_ret / ann_vol if ann_vol > 0 else np.nan

st.subheader("📊 績效指標")
c1, c2, c3 = st.columns(3)
c1.metric("年度化平均報酬率", f"{ann_ret*100:.2f}%")
c2.metric("年度化波動度",     f"{ann_vol*100:.2f}%")
c3.metric("夏普比率",         f"{sharpe:.2f}")

st.subheader("📈 累積報酬走勢")
st.line_chart(df.set_index('Date')['Cumulative Return'])
