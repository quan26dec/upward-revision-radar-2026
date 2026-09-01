import streamlit as st
import requests
import pandas as pd

JQUANTS_API_KEY = st.secrets["JQUANTS_API_KEY"]

st.title("📡 上方修正レーダー 2026")
st.info("上方修正候補スクリーナー 起動準備OK！")
url = "https://api.jquants.com/v2/equities/master"
headers = {"x-api-key": JQUANTS_API_KEY}
response = requests.get(url, headers=headers)
if response.status_code == 200:
    st.success("✅ J-Quants 接続成功！")
else:
    st.error(f"❌ J-Quants 接続失敗：{response.status_code}")

financial_url = "https://api.jquants.com/v2/fins/summary"
stock_code = st.text_input("銘柄コード", value="7751")
financial_response = requests.get(financial_url, params={"code": stock_code}, headers=headers)
st.write("決算API ステータス:", financial_response.status_code)

financial_data = financial_response.json()["data"]
financial_df = pd.DataFrame(financial_data)
latest_financial = financial_df.sort_values("DiscDate", ascending=False).iloc[0]
latest_fop = pd.to_numeric(latest_financial["FOP"], errors="coerce")
fop_valid = pd.notna(latest_fop) and latest_fop != 0
st.write("最新決算:", latest_financial[["DiscDate", "CurPerType", "Sales", "OP", "FSales", "FOP"]])
op_progress = float(latest_financial["OP"]) / latest_fop * 100 if fop_valid else None
st.write("📡 営業利益進捗率:", round(op_progress, 1) if op_progress is not None else "算出不可", "%" if op_progress is not None else "")
current_period = latest_financial["CurPerType"]
same_period_df = financial_df[financial_df["CurPerType"] == current_period].copy()
same_period_df = same_period_df.sort_values("DiscDate", ascending=False)
previous_same_period = same_period_df.iloc[1] if len(same_period_df) > 1 else None
previous_data_valid = previous_same_period is not None
st.write("前年同期決算:", previous_same_period[["DiscDate", "CurPerType", "Sales", "OP"]] if previous_same_period is not None else "データなし")
op_yoy = (float(latest_financial["OP"]) / float(previous_same_period["OP"]) - 1) * 100 if previous_data_valid else None
st.write("📈 営業利益 前年同期比:", round(op_yoy, 1) if op_yoy is not None else "算出不可", "%" if op_yoy is not None else "")
previous_fop = pd.to_numeric(previous_same_period["FOP"], errors="coerce") if previous_data_valid else None
previous_fop_valid = pd.notna(previous_fop) and previous_fop != 0
previous_op_progress = float(previous_same_period["OP"]) / previous_fop * 100 if previous_data_valid and previous_fop_valid else None
st.write("📊 前年同期の営業利益進捗率:", round(previous_op_progress, 1) if previous_op_progress is not None else "算出不可", "%" if previous_op_progress is not None else "")
progress_diff = op_progress - previous_op_progress if op_progress is not None and previous_op_progress is not None else None
st.write("📈 前年同期進捗差:", round(progress_diff, 1) if progress_diff is not None else "算出不可", "pt" if progress_diff is not None else "")
if current_period == "1Q":
    progress_threshold = 35
elif current_period == "2Q":
    progress_threshold = 70
elif current_period == "3Q":
    progress_threshold = 85
revision_candidate = (op_progress is not None) and (op_progress >= progress_threshold) and (op_yoy is not None) and (op_yoy > 0)
st.write("📡 上方修正候補:", "🔥 候補" if revision_candidate else "―")
