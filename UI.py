import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="Portfolio Allocator", layout="centered")
st.title("債券與股票配置計算器")

# 列出同目錄下的所有 CSV 檔案
csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
if not csv_files:
    st.error("目前目錄下沒有 CSV 檔案，請放入至少一個 .csv 檔")
else:
    selected = st.sidebar.multiselect("選擇要分析的 CSV 檔案", csv_files, default=csv_files)
    if not selected:
        st.sidebar.warning("請至少選擇一個 CSV 檔案")
    else:
        df_list = []
        for fname in selected:
            df = pd.read_csv(fname, encoding='utf-8', skipinitialspace=True)
            # 標準化欄位名稱
            df.columns = df.columns.str.strip().str.replace("'", "").str.replace(" ", "").str.lower()
            asset_name = os.path.splitext(fname)[0]
            if 'asset' not in df.columns:
                df['asset'] = asset_name

            # 偵測價格與股息欄位
            price_col = next((c for c in df.columns if 'price' in c), None)
            div_col = next((c for c in df.columns if 'dividend' in c or 'div' in c), None)
            if not price_col:
                st.warning(f"在檔案 {fname} 找不到價格欄位，請確認欄位名稱包含 'Price'。")
                continue
            # 轉數值
            df[price_col] = df[price_col].astype(str).str.replace("'", "").str.replace(",", "").astype(float)
            if div_col:
                df[div_col] = df[div_col].astype(str).str.replace("'", "").str.replace(",", "").replace('', '0').astype(float)
            else:
                df['dividend'] = 0.0
                div_col = 'dividend'

            # 統一命名
            df = df.rename(columns={price_col: 'price', div_col: 'dividend'})
            df_list.append(df[['asset', 'date', 'price', 'dividend']])

        if not df_list:
            st.error("所有選擇的檔案皆無法解析。請檢查欄位格式。")
        else:
            df = pd.concat(df_list, ignore_index=True)
            st.subheader("原始資料預覽")
            st.dataframe(df)

            df['return'] = (df['price'] + df['dividend']) / df.groupby('asset')['price'].shift(1) - 1
            assets = df['asset'].unique().tolist()
            st.sidebar.header("設定配置比例 (總和需=1)")
            weights = {a: st.sidebar.slider(a, 0.0, 1.0, 1.0/len(assets), 0.01) for a in assets}
            total = sum(weights.values())
            if abs(total-1)>1e-6:
                st.sidebar.error("總和不為1")
            else:
                series = [df[df['asset']==a]['return'].dropna().reset_index(drop=True) for a in assets]
                minl = min(len(s) for s in series)
                mat = np.vstack([s.values[-minl:] for s in series])
                w = np.array([weights[a] for a in assets])
                pr = w.dot(mat)
                ann = (pr.mean()+1)**252-1
                vol = pr.std()*np.sqrt(252)
                sharpe = ann/vol if vol else np.nan
                st.subheader("結果")
                st.write(f"年度化報酬: {ann*100:.2f}%")
                st.write(f"年度化波動: {vol*100:.2f}%")
                st.write(f"夏普比率: {sharpe:.2f}")
                st.line_chart(np.cumsum(pr))