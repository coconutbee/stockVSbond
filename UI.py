import streamlit as st
import pandas as pd
import numpy as np
import os
import altair as alt

st.set_page_config(page_title="Portfolio Allocator", layout="centered")
st.title("債券與股票配置計算器")

# 列出同目錄下的所有 CSV 檔案
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
if not csv_files:
    st.error("目前目錄下沒有 CSV 檔案，請放入至少一個 .csv 檔")
else:
    # 選取檔案
    selected = st.sidebar.multiselect("選擇要分析的 CSV 檔案", csv_files, default=csv_files)
    if not selected:
        st.sidebar.warning("請至少選擇一個 CSV 檔案")
    else:
        # 讀取並合併所有選定的檔案（解析 Date 欄位為 datetime）
        df_list = []
        for fname in selected:
            df = pd.read_csv(fname, encoding='utf-8', parse_dates=['Date'])
            asset_name = os.path.splitext(fname)[0]
            if 'Asset' not in df.columns:
                df['Asset'] = asset_name
            # 清理 Price 與 Dividend 欄位並轉成數值
            df['Price'] = df['Price'].astype(str).str.replace("'", "").str.replace(",", "").astype(float)
            if 'Dividend' in df.columns:
                df['Dividend'] = df['Dividend'].astype(str).str.replace("'", "").str.replace(",", "").fillna('0').astype(float)
            else:
                df['Dividend'] = 0.0
            df_list.append(df)
        df = pd.concat(df_list, ignore_index=True)

        st.subheader("原始資料預覽")
        st.dataframe(df)

        # 計算單位期間報酬率
        df['Return'] = (df['Price'] + df['Dividend']) / df.groupby('Asset')['Price'].shift(1) - 1

        # 側邊設定權重
        assets = df['Asset'].unique().tolist()
        st.sidebar.header("設定配置比例 (總和需=1)")
        weights = {asset: st.sidebar.slider(f"{asset} 比例", 0.0, 1.0, 1.0/len(assets), step=0.01) for asset in assets}
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            st.sidebar.error("比例總和不等於 1，請調整")
        else:
            # 計算組合報酬
            ret_series = [df[df['Asset']==asset]['Return'].dropna().reset_index(drop=True) for asset in assets]
            min_len = min(len(s) for s in ret_series)
            aligned = np.vstack([s.values[-min_len:] for s in ret_series])
            w = np.array([weights[a] for a in assets])
            port_returns = w.dot(aligned)

            # 取出對齊期間的日期，並包成帶時間索引的 Series
            date_series = (
                df[df['Asset']==assets[0]]['Date']
                  .dropna()
                  .reset_index(drop=True)
                  .iloc[-min_len:]
            )
            port_sr = pd.Series(port_returns, index=date_series, name='Portfolio')

            # 顯示結果
            ann_ret = (port_sr.mean()+1)**252 - 1
            ann_vol = port_sr.std() * np.sqrt(252)
            sharpe = ann_ret / ann_vol if ann_vol else np.nan

            st.subheader("結果")
            st.write(f"年度化平均報酬率：{ann_ret*100:.2f}%")
            st.write(f"年度化波動度：{ann_vol*100:.2f}%")
            st.write(f"夏普比率 (無風險利率0)：{sharpe:.2f}")

            # 準備繪圖資料
            df_plot = port_sr.cumsum().reset_index().rename(columns={'index':'Date', 'Portfolio':'Cumulative Return'})

            # —— 新增：互動式日期範圍選擇 —— #
            # 先轉成 Python datetime，再取 date()
            min_date = df_plot['Date'].dt.min().date()
            max_date = df_plot['Date'].dt.max().date()


            start_date, end_date = st.sidebar.date_input(
                "選擇圖表時間範圍",
                (min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

            # 建立 Altair 圖表，橫軸顯示年/月/日，並套用互動式範圍
            chart = (
                alt.Chart(df_plot)
                   .mark_line()
                   .encode(
                       x=alt.X(
                           'Date:T',
                           axis=alt.Axis(format='%Y/%m/%d', title='年/月/日'),
                           scale=alt.Scale(domain=[str(start_date), str(end_date)])
                       ),
                       y=alt.Y('Cumulative Return:Q', axis=alt.Axis(title='累積報酬'))
                   )
                   .properties(height=400)
            )
            st.altair_chart(chart, use_container_width=True)
