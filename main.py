import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 페이지 레이아웃 및 기본 설정
st.set_page_config(
    page_title="서울 100년 기온 변화 및 이상치 분석",
    page_icon="🌡️",
    layout="wide",
)

st.title("🌡️ 서울 100년 연평균 기온 변화 추이 (이상치 강조)")
st.markdown(
    "지난 100여 년간 서울의 기온 데이터 분석 및 데이터 누락/이상연도 강조"
    " 시각화를 제공하는 앱입니다."
)


# 데이터 불러오기 함수 (캐싱 적용)
@st.cache_data
def load_raw_data():
  url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"
  try:
    df = pd.read_csv(url, encoding="cp949")
  except Exception:
    df = pd.read_csv(url, encoding="utf-8")

  # 컬럼명 공백 제거
  df.columns = df.columns.str.strip()

  # 열 매칭
  date_col = [c for c in df.columns if "날짜" in c][0]
  avg_col = [c for c in df.columns if "평균" in c][0]
  min_col = [c for c in df.columns if "최저" in c][0]
  max_col = [c for c in df.columns if "최고" in c][0]

  # 숫자형 변환
  df[date_col] = pd.to_datetime(df[date_col])
  df["연도"] = df[date_col].dt.year
  for col in [avg_col, min_col, max_col]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

  return df, date_col, avg_col, min_col, max_col


df_raw, date_col, avg_col, min_col, max_col = load_raw_data()

# 전체 연도 범위 생성 (데이터가 비어있는 해 탐지용)
min_year_all = int(df_raw["연도"].min())
max_year_all = int(df_raw["연도"].max())
all_years = pd.DataFrame({"연도": range(min_year_all, max_year_all + 1)})

# 연도별 데이터 처리
df_annual = (
    df_raw.groupby("연도")[avg_col]
    .agg(연평균기온="mean", 데이터수="count")
    .reset_index()
)

# 전체 연도 기준 병합
df_annual = pd.merge(all_years, df_annual, on="연도", how="left")


# 이상 상태 분류 (정상, 누락/결측, 이상 저온)
def classify_year(row):
  if pd.isna(row["연평균기온"]) or row["데이터수"] < 100:
    return "누락 (데이터 누락)"
  elif row["연평균기온"] < 10.0:  # 10°C 미만 연도
    return "이상 저온 (<10.0°C)"
  else:
    return "정상 데이터"


df_annual["구분"] = df_annual.apply(classify_year, axis=1)

# 10년 이동평균 계산
df_annual["10년이동평균"] = (
    df_annual["연평균기온"].rolling(window=10, min_periods=5).mean()
)

# 탭 구성
tab1, tab2 = st.tabs(["📈 기온 변화 및 이상 데이터 그래프", "📊 원본 데이터 요약통계"])

with tab1:
  col1, col2, col3, col4 = st.columns(4)
  overall_avg = df_annual[df_annual["구분"] == "정상 데이터"][
      "연평균기온"
  ].mean()
  missing_years = df_annual[df_annual["구분"] == "누락 (데이터 누락)"][
      "연도"
  ].tolist()
  low_temp_years = df_annual[df_annual["구분"] == "이상 저온 (<10.0°C)"][
      "연도"
  ].tolist()

  col1.metric("관측 전체 기간", f"{min_year_all}년 ~ {max_year_all}년")
  col2.metric("정상 연도 평균 기온", f"{overall_avg:.2f} °C")
  col3.metric(
      "누락/결측 연도 수",
      f"{len(missing_years)}개 연도",
      help=f"해당 연도: {missing_years}",
  )
  col4.metric(
      "유난히 낮은 연도 수 (<10°C)",
      f"{len(low_temp_years)}개 연도",
      help=f"해당 연도: {low_temp_years}",
  )

  st.divider()

  # Plotly 시각화
  fig = go.Figure()

  # 1. 정상 연도 라인 + 마커
  df_normal = df_annual[df_annual["구분"] != "누락 (데이터 누락)"]
  fig.add_trace(
      go.Scatter(
          x=df_normal["연도"],
          y=df_normal["연평균기온"],
          mode="lines+markers",
          name="연평균 기온 (정상)",
          line=dict(color="#3182CE", width=1.5),
          marker=dict(size=6, color="#3182CE"),
          hovertemplate="%{x}년 연평균: %{y:.2f} °C",
      )
  )

  # 2. 10년 이동평균 추세선
  fig.add_trace(
      go.Scatter(
          x=df_annual["연도"],
          y=df_annual["10년이동평균"],
          mode="lines",
          name="10년 이동평균 추세",
          line=dict(color="#2B6CB0", width=2.5, dash="dash"),
          hovertemplate="%{x}년 (10년 평균): %{y:.2f} °C",
      )
  )

  # 3. 유난히 낮은 연도 강조 (빨간색 다이아몬드 마커)
  df_low = df_annual[df_annual["구분"] == "이상 저온 (<10.0°C)"]
  fig.add_trace(
      go.Scatter(
          x=df_low["연도"],
          y=df_low["연평균기온"],
          mode="markers+text",
          name="유난히 낮은 연도 (<10°C)",
          marker=dict(
              size=14,
              color="#E53E3E",
              symbol="diamond",
              line=dict(color="black", width=1),
          ),
          text=[
              f"{y}년 ({t:.1f}°C)"
              for y, t in zip(df_low["연도"], df_low["연평균기온"])
          ],
          textposition="bottom center",
          textfont=dict(color="#E53E3E", size=11),
          hovertemplate="⚠️ 이상 저온 연도: %{x}년 (%{y:.2f} °C)",
      )
  )

  # 4. 데이터가 비어 있는 연도 표시 (X축 하단 주황색 엑스 마커)
  df_missing = df_annual[df_annual["구분"] == "누락 (데이터 누락)"]
  if not df_missing.empty:
    min_y_val = (
        df_annual["연평균기온"].min() - 0.8
        if not pd.isna(df_annual["연평균기온"].min())
        else 8
    )
    fig.add_trace(
        go.Scatter(
            x=df_missing["연도"],
            y=[min_y_val] * len(df_missing),
            mode="markers",
            name="데이터 누락/비어 있음",
            marker=dict(
                size=12, color="#DD6B20", symbol="x", line=dict(width=2)
            ),
            hovertemplate="❌ 데이터 누락 연도: %{x}년",
        )
    )

    # 주석 라벨 추가
    for _, row in df_missing.iterrows():
      fig.add_annotation(
          x=row["연도"],
          y=min_y_val,
          text=f"<b>{int(row['연도'])}년 누락</b>",
          showarrow=True,
          arrowhead=2,
          arrowcolor="#DD6B20",
          arrowsize=1,
          arrowwidth=1.5,
          ax=0,
          ay=-35,
          font=dict(color="#DD6B20", size=11),
      )

  fig.update_layout(
      title=dict(
          text="서울 연평균 기온 추이 (결측 및 이상 저온 연도 강조)",
          font=dict(size=18),
      ),
      xaxis_title="연도 (년)",
      yaxis_title="기온 (°C)",
      hovermode="closest",
      legend=dict(
          orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
      ),
      template="plotly_white",
      height=580,
  )

  st.plotly_chart(fig, use_container_width=True)

  # 이상 포인트 안내 메시지
  st.warning(
      "💡 **그래프 이상 포인트 안내**\n"
      "- ❌ **주황색 X 표시**: 한국전쟁(1950~1953년) 등으로 인해 일별 데이터 관측이"
      " 누락되거나 비어 있는 연도입니다.\n"
      "- 🔷 **빨간색 다이아몬드 표시**: 연평균 기온이 유난히 낮게(10°C 미만) 기록된"
      " 이상 저온 연도입니다."
  )

with tab2:
  st.subheader("📋 원본 데이터 기술통계 (Summary Statistics)")
  st.markdown(
      "일별 원본 데이터(`seoul.csv`)의 주요 기온 항목별 기술통계량입니다."
  )

  temp_data = df_raw[[avg_col, min_col, max_col]]
  stats_df = temp_data.describe().T

  stats_df = stats_df.rename(
      columns={
          "count": "개수(일)",
          "mean": "평균(°C)",
          "std": "표준편차",
          "min": "최소(°C)",
          "25%": "25% 백분위",
          "50%": "중앙값(50%)",
          "75%": "75% 백분위",
          "max": "최대(°C)",
      }
  )

  st.dataframe(stats_df.style.format("{:.2f}"), use_container_width=True)

  st.divider()

  st.subheader("🔎 결측 및 이상 연도 상세 데이터")
  st.dataframe(
      df_annual[df_annual["구분"] != "정상 데이터"][
          ["연도", "연평균기온", "데이터수", "구분"]
      ].rename(columns={"데이터수": "관측일수(일)", "연평균기온": "연평균기온(°C)"}),
      use_container_width=True,
  )

# 사이드바
st.sidebar.header("⚙️ 데이터 옵션")
if st.sidebar.checkbox("전체 연도 데이터표 보기", value=False):
  st.sidebar.subheader("연도별 데이터")
  st.sidebar.dataframe(df_annual[["연도", "연평균기온", "구분"]])
