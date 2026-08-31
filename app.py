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
financial_response = requests.get(financial_url, params={"code": "7751"}, headers=headers)
st.write("決算API ステータス:", financial_response.status_code)
st.write("決算API 応答内容:", financial_response.text)

financial_data = financial_response.json()["data"]
financial_df = pd.DataFrame(financial_data)
latest_financial = financial_df.sort_values("DiscDate", ascending=False).iloc[0]
st.write("最新決算:", latest_financial[["DiscDate", "CurPerType", "Sales", "OP", "FSales", "FOP"]])
op_progress = float(latest_financial["OP"]) / float(latest_financial["FOP"]) * 100
st.write("📡 営業利益進捗率:", round(op_progress, 1), "%")
current_period = latest_financial["CurPerType"]
same_period_df = financial_df[financial_df["CurPerType"] == current_period].copy()
same_period_df = same_period_df.sort_values("DiscDate", ascending=False)
previous_same_period = same_period_df.iloc[1] if len(same_period_df) > 1 else None
st.write("前年同期決算:", previous_same_period[["DiscDate", "CurPerType", "Sales", "OP"]] if previous_same_period is not None else "データなし")
