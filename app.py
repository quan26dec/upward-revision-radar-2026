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

master_data = response.json()["data"]
master_df = pd.DataFrame(master_data)

st.write("銘柄マスター件数:", len(master_df))
st.dataframe(master_df.head())

stock_master_df = master_df[
    master_df["ProdCat"].astype(str) == "011"
].copy()

stock_master_df["Code4"] = (
    stock_master_df["Code"]
    .astype(str)
    .str[:4]
)

test_50_codes = stock_master_df["Code4"].head(50).tolist()

st.write("📡 普通株50銘柄テスト")
st.write("普通株件数:", len(stock_master_df))
st.write(test_50_codes)

financial_url = "https://api.jquants.com/v2/fins/summary"
stock_code = st.text_input("銘柄コード", value="7751")
test_codes = ["7751", "7965", "6501", "7203", "8035"]
st.write("📡 5銘柄テスト:", test_codes)
for code in test_codes:
    st.write("テスト銘柄:", code)
    test_response = requests.get(financial_url, params={"code": code}, headers=headers)
    st.write("API:", code, test_response.status_code)
    st.write("データ件数:", len(test_response.json()["data"]))
    test_df = pd.DataFrame(test_response.json()["data"])
    test_latest = test_df.sort_values("DiscDate", ascending=False).iloc[0]
    st.write("最新決算:", code, test_latest["DiscDate"], test_latest["CurPerType"])
financial_response = requests.get(financial_url, params={"code": stock_code}, headers=headers)
st.write("決算API ステータス:", financial_response.status_code)

financial_data = financial_response.json()["data"]
financial_df = pd.DataFrame(financial_data)
latest_financial = financial_df.sort_values("DiscDate", ascending=False).iloc[0]
latest_fop = pd.to_numeric(latest_financial["FOP"], errors="coerce")
latest_op = pd.to_numeric(latest_financial["OP"], errors="coerce")
op_valid = pd.notna(latest_op)
fop_valid = pd.notna(latest_fop) and latest_fop != 0
st.write("最新決算:", latest_financial[["DiscDate", "CurPerType", "Sales", "OP", "FSales", "FOP"]])
op_progress = latest_op / latest_fop * 100 if op_valid and fop_valid else None
st.write("📡 営業利益進捗率:", round(op_progress, 1) if op_progress is not None else "算出不可", "%" if op_progress is not None else "")
current_period = latest_financial["CurPerType"]
current_fy_end = latest_financial["CurFYEn"]
previous_fy_end = str(int(str(current_fy_end)[:4]) - 1) + str(current_fy_end)[4:]
same_period_df = financial_df[financial_df["CurPerType"] == current_period].copy()
previous_same_period_df = same_period_df[same_period_df["CurFYEn"].astype(str) == previous_fy_end].copy()
same_period_df = same_period_df.sort_values("DiscDate", ascending=False)
previous_same_period = previous_same_period_df.sort_values("DiscDate", ascending=False).iloc[0] if len(previous_same_period_df) > 0 else None
previous_data_valid = previous_same_period is not None
st.write("前年同期決算:", previous_same_period[["DiscDate", "CurPerType", "Sales", "OP"]] if previous_same_period is not None else "データなし")


previous_op = pd.to_numeric(previous_same_period["OP"], errors="coerce") if previous_data_valid else None
previous_op_valid = pd.notna(previous_op) and previous_op != 0
op_yoy = (latest_op / previous_op - 1) * 100 if op_valid and previous_op_valid else None
st.write("📈 営業利益 前年同期比:", round(op_yoy, 1) if op_yoy is not None else "算出不可", "%" if op_yoy is not None else "")
previous_fop = pd.to_numeric(previous_same_period["FOP"], errors="coerce") if previous_data_valid else None
previous_fop_valid = pd.notna(previous_fop) and previous_fop != 0
previous_op_progress = previous_op / previous_fop * 100 if previous_op_valid and previous_fop_valid else None
st.write("📊 前年同期の営業利益進捗率:", round(previous_op_progress, 1) if previous_op_progress is not None else "算出不可", "%" if previous_op_progress is not None else "")
progress_diff = op_progress - previous_op_progress if op_progress is not None and previous_op_progress is not None else None
st.write("📈 前年同期進捗差:", round(progress_diff, 1) if progress_diff is not None else "算出不可", "pt" if progress_diff is not None else "")
if current_period == "1Q":
    progress_threshold = 35
elif current_period == "2Q":
    progress_threshold = 70
elif current_period == "3Q":
    progress_threshold = 85
else:
    progress_threshold = None
revision_candidate = (progress_threshold is not None) and (op_progress is not None) and (op_progress >= progress_threshold) and (op_yoy is not None) and (op_yoy > 0)
st.write("📡 上方修正候補:", "🔥 候補" if revision_candidate else "―")

def analyze_stock(code):
    try:
        response = requests.get(
            financial_url,
            params={"code": code},
            headers=headers
        )

        if response.status_code != 200:
            return None

        data = response.json()["data"]

        if len(data) == 0:
            return None

        df = pd.DataFrame(data)

        latest = df.sort_values("DiscDate", ascending=False).iloc[0]

        latest_op = pd.to_numeric(latest["OP"], errors="coerce")
        latest_fop = pd.to_numeric(latest["FOP"], errors="coerce")

        if pd.isna(latest_op) or pd.isna(latest_fop) or latest_fop == 0:
            return None

        op_progress = latest_op / latest_fop * 100

        current_period = latest["CurPerType"]
        current_fy_end = latest["CurFYEn"]

        previous_fy_end = (
            str(int(str(current_fy_end)[:4]) - 1)
            + str(current_fy_end)[4:]
        )

        previous_df = df[
            (df["CurPerType"] == current_period)
            & (df["CurFYEn"].astype(str) == previous_fy_end)
        ].copy()

        if len(previous_df) == 0:
            return None

        previous = previous_df.sort_values(
            "DiscDate",
            ascending=False
        ).iloc[0]

        previous_op = pd.to_numeric(
            previous["OP"],
            errors="coerce"
        )

        previous_fop = pd.to_numeric(
            previous["FOP"],
            errors="coerce"
        )

        if pd.isna(previous_op):
            return None

        # 前年同期比
        if previous_op > 0:
            op_yoy = (latest_op / previous_op - 1) * 100
        else:
            op_yoy = None

        # 前年同期進捗率
        if (
            pd.notna(previous_fop)
            and previous_fop != 0
        ):
            previous_progress = (
                previous_op / previous_fop * 100
            )
        else:
            previous_progress = None

        # 進捗差
        if previous_progress is not None:
            progress_diff = (
                op_progress - previous_progress
            )
        else:
            progress_diff = None

        # 四半期ごとの基準
        if current_period == "1Q":
            progress_threshold = 35

        elif current_period == "2Q":
            progress_threshold = 70

        elif current_period == "3Q":
            progress_threshold = 85

        else:
            progress_threshold = None

        # 上方修正候補判定
        revision_candidate = (
            progress_threshold is not None
            and op_progress >= progress_threshold
            and op_yoy is not None
            and op_yoy > 0
        )

        return {
            "Code": code,
            "DiscDate": latest["DiscDate"],
            "Period": current_period,
            "OP": latest_op,
            "FOP": latest_fop,
            "OPProgress": round(op_progress, 1),
            "OPYoY": round(op_yoy, 1)
            if op_yoy is not None else None,
            "PrevProgress": round(previous_progress, 1)
            if previous_progress is not None else None,
            "ProgressDiff": round(progress_diff, 1)
            if progress_diff is not None else None,
            "RevisionCandidate": revision_candidate
        }

    except Exception as e:
        st.write("エラー:", code, e)
        return None
st.subheader("📡 5銘柄スクリーニングテスト")

screen_results = []

for code in test_codes:
    result = analyze_stock(code)

    if result is not None:
        screen_results.append(result)

screen_df = pd.DataFrame(screen_results)

st.dataframe(screen_df)

st.subheader("🔥 上方修正候補")

candidate_df = screen_df[
    screen_df["RevisionCandidate"] == True
].copy()

if len(candidate_df) > 0:
    st.dataframe(candidate_df)
else:
    st.write("現在、条件を満たす候補はありません")

st.subheader("📡 普通株50銘柄スクリーニング")

if st.button("🚀 50銘柄をスクリーニング"):

    results_50 = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(test_50_codes)

    for i, code in enumerate(test_50_codes):

        status_text.write(
            f"分析中: {i + 1} / {total}　銘柄コード {code}"
        )

        result = analyze_stock(code)

        if result is not None:
            results_50.append(result)

        progress_bar.progress((i + 1) / total)

    screen_50_df = pd.DataFrame(results_50)

    status_text.write("✅ 50銘柄スクリーニング完了")

    st.write(
        "分析できた銘柄数:",
        len(screen_50_df)
    )

    if len(screen_50_df) > 0:

        st.dataframe(screen_50_df)

        candidate_50_df = screen_50_df[
            screen_50_df["RevisionCandidate"] == True
        ].copy()

        st.subheader("🔥 50銘柄の上方修正候補")

    if len(candidate_50_df) > 0:
    
        name_df = stock_master_df[
            ["Code4", "CoName"]
        ].drop_duplicates()
    
        candidate_50_df = candidate_50_df.merge(
            name_df,
            left_on="Code",
            right_on="Code4",
            how="left"
        )
    
        candidate_50_df = candidate_50_df[
            [
                "Code",
                "CoName",
                "Period",
                "OPProgress",
                "PrevProgress",
                "ProgressDiff",
                "OPYoY",
                "DiscDate",
                "RevisionCandidate"
            ]
        ]

        candidate_50_df = candidate_50_df.sort_values(
            ["ProgressDiff", "OPYoY"],
            ascending=[False, False]
        )
        
        st.dataframe(candidate_50_df)
    
    else:
        st.write("条件を満たす候補はありません")

st.subheader("🔍 業績予想修正履歴テスト")

revision_test_code = "1434"

revision_response = requests.get(
    financial_url,
    params={"code": revision_test_code},
    headers=headers
)

revision_df = pd.DataFrame(
    revision_response.json()["data"]
)

st.dataframe(
    revision_df[
        [
            "DiscDate",
            "CurPerType",
            "CurFYEn",
            "OP",
            "FOP"
        ]
    ].sort_values(
        "DiscDate",
        ascending=False
    ).head(15)
)

# 今期のFOP変更チェック
current_fy = revision_df.sort_values(
    "DiscDate",
    ascending=False
).iloc[0]["CurFYEn"]

current_fy_df = revision_df[
    revision_df["CurFYEn"].astype(str) == str(current_fy)
].copy()

fop_history = pd.to_numeric(
    current_fy_df["FOP"],
    errors="coerce"
).dropna()

fop_changed = (
    fop_history.nunique() > 1
)

st.write(
    "📡 今期FOP変更:",
    "⚠️ 変更あり" if fop_changed else "🔥 据え置き"
)

st.write(
    "今期FOPの種類:",
    fop_history.unique()
)
