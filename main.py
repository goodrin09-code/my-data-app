import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일별 박스오피스")


# --------------------------------------------------
# 2. 한국 시간 기준 날짜 계산
# --------------------------------------------------
# 서버 시간이 한국 시간이 아닐 수 있으므로
# Asia/Seoul 시간대를 사용한다.

korea_time = datetime.now(ZoneInfo("Asia/Seoul"))

today = korea_time.date()
yesterday = today - timedelta(days=1)


# --------------------------------------------------
# 3. 날짜 선택
# --------------------------------------------------
# 가장 최근에 선택할 수 있는 날짜는 어제까지이다.

selected_date = st.date_input(
    "조회할 날짜를 선택하세요.",
    value=yesterday,
    min_value=datetime(2000, 1, 1).date(),
    max_value=yesterday
)

# KOBIS API가 요구하는 YYYYMMDD 형식으로 변환
target_date = selected_date.strftime("%Y%m%d")

st.caption(
    f"조회 날짜: {selected_date.strftime('%Y년 %m월 %d일')}"
)


# --------------------------------------------------
# 4. KOBIS API 요청 함수
# --------------------------------------------------
# 같은 날짜를 다시 조회하면 1시간 동안 저장된 결과를 사용한다.

@st.cache_data(ttl=3600)
def get_boxoffice(target_date):
    # Streamlit Cloud Secrets에서 인증키를 가져온다.
    api_key = st.secrets["KOBIS_KEY"]

    url = (
        "https://www.kobis.or.kr/kobisopenapi/"
        "webservice/rest/boxoffice/"
        "searchDailyBoxOfficeList.json"
    )

    params = {
        "key": api_key,
        "targetDt": target_date
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    # HTTP 오류가 발생하면 예외를 발생시킨다.
    response.raise_for_status()

    return response.json()


# --------------------------------------------------
# 5. API 호출
# --------------------------------------------------

try:
    data = get_boxoffice(target_date)

except KeyError:
    st.error(
        "KOBIS 인증키를 찾을 수 없습니다.\n\n"
        "확인할 것:\n"
        "1. Streamlit Cloud의 Secrets에 KOBIS_KEY가 있는지 확인하세요.\n"
        "2. 이름이 정확히 KOBIS_KEY인지 확인하세요.\n"
        "3. 인증키가 올바르게 입력되어 있는지 확인하세요."
    )
    st.stop()

except requests.exceptions.RequestException as e:
    st.error(
        "KOBIS API 요청에 실패했습니다.\n\n"
        "확인할 것:\n"
        "1. 인터넷 연결 상태\n"
        "2. KOBIS API 서버 상태\n"
        "3. KOBIS 인증키가 유효한지\n\n"
        f"오류 내용: {e}"
    )
    st.stop()

except Exception as e:
    st.error(
        "데이터를 가져오는 중 문제가 발생했습니다.\n\n"
        "인증키와 KOBIS API 설정을 확인해 주세요.\n\n"
        f"오류 내용: {e}"
    )
    st.stop()


# --------------------------------------------------
# 6. KOBIS faultInfo 확인
# --------------------------------------------------
# 인증키가 틀려도 HTTP 상태코드는 200일 수 있으므로
# faultInfo가 있는지 직접 확인한다.

if "faultInfo" in data:
    fault = data["faultInfo"]

    fault_message = fault.get(
        "message",
        "KOBIS API에서 오류가 발생했습니다."
    )

    st.error(
        "KOBIS API에서 오류가 발생했습니다.\n\n"
        f"오류 내용: {fault_message}\n\n"
        "확인할 것:\n"
        "1. Streamlit Cloud의 Secrets에 입력한 KOBIS_KEY가 정확한지 확인하세요.\n"
        "2. KOBIS에서 발급받은 인증키가 유효한지 확인하세요.\n"
        "3. 선택한 날짜가 올바른지 확인하세요."
    )
    st.stop()


# --------------------------------------------------
# 7. 영화 목록 가져오기
# --------------------------------------------------

boxoffice_result = data.get("boxOfficeResult", {})

movie_list = boxoffice_result.get(
    "dailyBoxOfficeList",
    []
)


# --------------------------------------------------
# 8. 영화 목록이 없는 경우
# --------------------------------------------------

if not movie_list:
    st.warning(
        "그날은 아직 집계 전입니다."
    )

    st.info(
        "다른 날짜를 선택해 주세요. "
        "KOBIS에서 해당 날짜의 일별 박스오피스가 아직 제공되지 않았을 수 있습니다."
    )

    st.stop()


# --------------------------------------------------
# 9. 영화 데이터 정리
# --------------------------------------------------
# KOBIS API의 숫자는 문자열로 오기 때문에
# 정렬과 그래프에 사용할 수 있도록 숫자로 변환한다.

movies = []

for movie in movie_list:

    rank_inten = int(movie.get("rankInten", 0))

    # 순위 변동 표시
    if rank_inten > 0:
        rank_change = f"🔺 {rank_inten}"
    elif rank_inten < 0:
        rank_change = f"🔻 {abs(rank_inten)}"
    else:
        rank_change = "-"

    # 누적 관객수가 100만 명을 넘었으면 트로피 추가
    audi_acc = int(movie["audiAcc"])

    if audi_acc >= 1_000_000:
        movie_name = f"{movie['movieNm']} 🏆"
    else:
        movie_name = movie["movieNm"]

    movies.append({
        "순위": int(movie["rank"]),
        "증감": rank_change,
        "영화명": movie_name,
        "개봉일": movie["openDt"],
        "관객수": int(movie["audiCnt"]),
        "누적관객": audi_acc,
        "스크린수": int(movie["scrnCnt"]),
    })


# --------------------------------------------------
# 10. 박스오피스 표
# --------------------------------------------------

st.subheader("📋 일별 박스오피스")

st.dataframe(
    movies,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(
            "순위",
            format="%d위"
        ),
        "증감": st.column_config.TextColumn(
            "전일 대비"
        ),
        "관객수": st.column_config.NumberColumn(
            "관객수",
            format="%d명"
        ),
        "누적관객": st.column_config.NumberColumn(
            "누적관객",
            format="%d명"
        ),
        "스크린수": st.column_config.NumberColumn(
            "스크린수",
            format="%d개"
        ),
    }
)


# --------------------------------------------------
# 11. 1위 영화
# --------------------------------------------------

first_movie = movies[0]

st.subheader("🥇 1위 영화")

st.markdown(
    f"### {first_movie['영화명']}"
)


# 지표 카드 3개
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "관객수",
        f"{first_movie['관객수']:,}명"
    )

with col2:
    st.metric(
        "누적 관객수",
        f"{first_movie['누적관객']:,}명"
    )

with col3:
    st.metric(
        "스크린수",
        f"{first_movie['스크린수']:,}개"
    )


# --------------------------------------------------
# 12. 관객수 상위 5편 그래프
# --------------------------------------------------

st.subheader("📊 관객수 상위 5편")

# 관객수를 기준으로 내림차순 정렬
top5 = sorted(
    movies,
    key=lambda movie: movie["관객수"],
    reverse=True
)[:5]


# 그래프용 데이터
chart_data = {
    movie["영화명"]: movie["관객수"]
    for movie in top5
}

st.bar_chart(
    chart_data,
    y_label="관객수",
    x_label="영화명"
)
