import streamlit as st
import requests
import pandas as pd
import time

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

test_50_codes = stock_master_df["Code4"].head(200).tolist()

st.write("📡 普通株200銘柄テスト")
st.write("普通株件数:", len(stock_master_df))
st.write(test_50_codes)

financial_url = "https://api.jquants.com/v2/fins/summary"

def analyze_stock(code):
    try:
        response = requests.get(
            financial_url,
            params={"code": code},
            headers=headers
        )

        retry_count = 0
        
        while response.status_code == 429 and retry_count < 3:
            retry_count += 1
        
            st.write(
                f"⏳ 429発生。3秒待って再試行 {retry_count}/3:",
                code
            )
        
            time.sleep(3)
        
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

        # 今期FOP変更チェック
        current_fy_df = df[
            df["CurFYEn"].astype(str) == str(current_fy_end)
        ].copy()
        
        fop_history = pd.to_numeric(
            current_fy_df["FOP"],
            errors="coerce"
        ).dropna()
        
        fop_changed = (
            fop_history.nunique() > 1
        )
        
        fop_status = (
            "⚠️ 変更あり"
            if fop_changed
            else "🔥 据え置き"
        )

        # 四半期ごとの基準
        if current_period == "1Q":
            progress_threshold = 35

        elif current_period == "2Q":
            progress_threshold = 70

        elif current_period == "3Q":
            progress_threshold = 85

        else:
            progress_threshold = None

        if progress_threshold is not None:
            threshold_gap = op_progress - progress_threshold
        else:
            threshold_gap = None
        
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
            "ThresholdGap": round(threshold_gap, 1)
            if threshold_gap is not None else None,
            "FOPChanged": fop_changed,
            "FOPStatus": fop_status,
            "RevisionCandidate": revision_candidate
        }

    except Exception as e:
        st.write("エラー:", code, e)
        return None

st.subheader("📡 普通株200銘柄スクリーニング")

if st.button("🚀 200銘柄をスクリーニング"):

    results_50 = []
    excluded_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(test_50_codes)

    for i, code in enumerate(test_50_codes):

        status_text.write(
            f"分析中: {i + 1} / {total}　銘柄コード {code}"
        )

        result = analyze_stock(code)

        time.sleep(0.8)

        if result is not None:
            results_50.append(result)
        else:
            excluded_count += 1

        progress_bar.progress((i + 1) / total)

    screen_50_df = pd.DataFrame(results_50)

    status_text.write("✅ 200銘柄スクリーニング完了")

    st.write(
        "📡 判定対象:",
        len(screen_50_df),
        "/",
        total,
        "社"
    )

    st.write(
        "⏭️ 判定対象外:",
        excluded_count,
        "社"
    )
    
    if len(screen_50_df) > 0:

        st.dataframe(screen_50_df)

        name_df = stock_master_df[
            ["Code4", "CoName"]
        ].drop_duplicates()
        
        near_candidate_df = screen_50_df[
            (screen_50_df["ThresholdGap"] >= -5)
            & (screen_50_df["ThresholdGap"] < 0)
            & (screen_50_df["ProgressDiff"] > 0)
            & (screen_50_df["OPYoY"] > 0)
        ].copy()

        near_candidate_df["NearScore"] = (
            5 + near_candidate_df["ThresholdGap"]
            + near_candidate_df["ProgressDiff"] / 10
            + near_candidate_df["OPYoY"].clip(upper=100) / 10       
        )
        
        candidate_50_df = screen_50_df[
            screen_50_df["RevisionCandidate"] == True
        ].copy()

        st.subheader("🔥 200銘柄の上方修正候補")

    if len(candidate_50_df) > 0:
    
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
                "ThresholdGap",
                "PrevProgress",
                "ProgressDiff",
                "OPYoY",
                "FOPStatus",
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

    st.subheader("👀 基準直前候補")

    if len(near_candidate_df) > 0:

        near_candidate_df = near_candidate_df.merge(
            name_df,
            left_on="Code",
            right_on="Code4",
            how="left"
        )            

        near_candidate_df = near_candidate_df[
            [
                "Code",
                "CoName",
                "Period",
                "OPProgress",
                "ThresholdGap",
                "NearScore",
                "PrevProgress",
                "ProgressDiff",
                "OPYoY",
                "FOPStatus",
                "DiscDate"
            ]
        ]

        near_candidate_df = near_candidate_df.sort_values(
            "NearScore",
            ascending=False
        )
        
        st.dataframe(near_candidate_df)
    else:
        st.write("基準直前の候補はありません")

st.subheader("🧪 決算日指定テスト")

if st.button("日付指定テスト"):

    test_response = requests.get(
        financial_url,
        params={"date": "2026-08-07"},
        headers=headers
    )

    st.write("ステータス:", test_response.status_code)

    if test_response.status_code == 200:
        test_json = test_response.json()

        st.write("JSONキー:", test_json.keys())

        if "data" in test_json:
            st.write("取得件数:", len(test_json["data"]))
            st.dataframe(
                pd.DataFrame(test_json["data"]).head(10)
            )

        if "pagination_key" in test_json:
            st.write(
                "pagination_key:",
                test_json["pagination_key"]
            )
