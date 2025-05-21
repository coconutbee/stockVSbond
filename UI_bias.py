import streamlit as st
import pandas as pd
import numpy as np
import os
import altair as alt  # 新增 Altair

st.set_page_config(page_title="Bond‐Stock 配置計算器", layout="wide")
st.title("20+年期公債、1~3年期公債 與 SPY 配置分析")
st.subheader("取樣自2005/05/18~2025/05/16")

# 找出所有 CSV 檔
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
if not csv_files:
    st.error("目前目錄下沒有 .csv 檔，請先放入至少三個格式為 Date, Price, Dividend 的檔案")
    st.stop()

# Sidebar：選擇三類資產的檔案
st.sidebar.header("操作步驟:")
st.sidebar.header("1️⃣ 選擇 CSV 檔案")
file_20plus = st.sidebar.selectbox("20年以上公債 CSV 檔", csv_files, index=1)
file_1to3   = st.sidebar.selectbox("1~3年期公債 CSV 檔", csv_files, index=0 if len(csv_files)>1 else 0)
file_spy    = st.sidebar.selectbox("SPY大盤股票 CSV 檔", csv_files, index=2 if len(csv_files)>2 else 0)

# Sidebar：調整三資產配置比例（用單條 Range Slider 產生兩個分割點）
st.sidebar.header("2️⃣ 調整資產配置 (總和必須=1)")
# 這裡用 range slider，value=(分點1, 分點2)，分別對應 20+、1~3、SPY 三段
split1, split2 = st.sidebar.slider(
    "長期公債 | 短期公債 | 大盤股市",
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
    dy=-15  # 往上偏移文字
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

# ----------------------------
# 先把 df 重設 index，方便用 iloc 切片
df['Date'] = (
    df['Date']
          # 1. 去掉單引號、雙引號
      .str.replace("'",  "", regex=False)
      .str.replace('"',  "", regex=False)
      # 2. 把「年」->"-"、「月」->"-」、「日」->"" 
      .str.replace('年', '-', regex=False)
      .str.replace('月', '-', regex=False)
      .str.replace('日',  '', regex=False)
      .str.replace(r'(\d{4})年(\d{1,2})月(\d{1,2})日', r'\1-\2-\3', regex=True)
)
df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
df = df.reset_index(drop=True)
df['Year'] = df['Date'].dt.year
# 🗓️ 計算每 252 天為一期的年化績效
window = 252
metrics = []
years = set(df['Year'])

for year, grp in df.groupby('Year'):
    # 如果不是第一年，就把 grp 的第一筆 drop 掉
    if (year-1) in years and len(grp) > 0:
        grp = grp.iloc[1:]
    
    # 該年的總報酬（幾何相乘 -1）
    total_ret = (1 + grp['PortRet']).prod() - 1
    # 該年實際交易日數
    n = len(grp)
    # 年化平均報酬：根據實際天數 n 年化到 252 天
    ann_ret_i = (1 + total_ret) ** (252 / n) - 1
    # 年化波動度：日波動 * sqrt(252)
    ann_vol_i = grp['PortRet'].std() * np.sqrt(252)
    
    metrics.append({
        'Year': year,
        '年化報酬率': ann_ret_i,
        '年度波動率': ann_vol_i
    })

# 🎯 加入 Streamlit 年度範圍選擇器
st.subheader("📆 自訂區間績效計算")

min_year = df['Year'].min()
max_year = df['Year'].max()
start_year, end_year = st.slider("選擇起迄年份", min_value=int(min_year), max_value=int(max_year), value=(2010, 2020))

# 篩選出該期間資料
df_period = df[(df['Year'] >= start_year) & (df['Year'] <= end_year)].copy()
df_period['Cumulative Return'] = (1 + df_period['PortRet']).cumprod() - 1

# 安全檢查：是否有資料
if df_period.empty:
    st.warning("❗ 選定的區間內無資料，請重新選擇年份")
else:
    # 總報酬率
    total_return = (1 + df_period["PortRet"]).prod() - 1
    # 有幾個交易日
    n_days = len(df_period)
    # 年化報酬率
    ann_return = (1 + total_return) ** (252 / n_days) - 1
    # 年化波動率
    ann_volatility = df_period["PortRet"].std() * np.sqrt(252)

    # 顯示結果
    st.markdown(f"✅ **{start_year} ~ {end_year}** 區間：")
    st.markdown(f"<h4>🔸 年化報酬率（CAGR）: {ann_return:.2%}</h4>", unsafe_allow_html=True)
    st.markdown(f"<h4>🔸 年化波動率（Volatility）: {ann_volatility:.2%}</h4>", unsafe_allow_html=True)
    risk_free_rate = 0.02  # 無風險利率，例如 2%
    sharpe_ratio = (ann_return - risk_free_rate) / ann_volatility
    st.markdown(f"<h4>🔸 夏普比率（Sharpe Ratio）: {sharpe_ratio:.2f}</h4> ", unsafe_allow_html=True)
    st.markdown(f"(無風險利率，假設 2%)")
    base_value = df_period.iloc[0]['Cumulative Return']




st.subheader(f"📈 {start_year} ~ {end_year} 的累積報酬走勢")

# 篩選區間資料
# 直接拿剛剛算好的 df_period（一開始就只包含選定的年份）
df_chart = df_period.copy()

# 重新從 1 開始累積報酬
df_chart['CumRetRebased'] = (1 + df_chart['PortRet']).cumprod() - 1

line = alt.Chart(df_chart).mark_line(color="steelblue").encode(
    x=alt.X("Date:T", title="日期"),
    y=alt.Y("CumRetRebased:Q", title="累積報酬率", scale=alt.Scale(zero=False)),
    tooltip=[
        alt.Tooltip("Date:T", title="日期"),
        alt.Tooltip("CumRetRebased:Q", title="累積報酬", format=".2%")
    ]
).properties(
    height=400,
    width="container"
).interactive()

st.altair_chart(line, use_container_width=True)


# metrics_df = pd.DataFrame(metrics).sort_values('Year')
# st.subheader("📅 每自然年度的年化績效")
# st.dataframe(
#     metrics_df
#       .set_index('Year')
#       .style
#       .format("{:.2%}")
# )
# ----------------------------
