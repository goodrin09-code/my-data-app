import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")


# --------------------------------------------------
# 2. 한국 시간 기준으로 '어제' 계산하기
# --------------------------------------------------
# 스트림릿 클라우드 서버의 시간은 한국 시간이 아닐 수 있으므로
# 반드시 Asia/Seoul 시간대를 사용한다.

korea_time = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = korea_time.date() - timedelta(days=1)

# KOBIS API가 요구하는 YYYYMMDD 형식으로 변환
target_date = yesterday.strftime("%Y%m%d")

st.caption(
    f"조회 날짜: {yesterday.strftime('%Y년 %m월 %d일')} "
    f"(한국 시간 기준)"
)


# --------------------------------------------------
# 3. API 요청 함수
# --------------------------------------------------
# st.cache_data를 사용하면 같은 날짜를 다시 조회할 때
# API를 매번 호출하지 않고 약 1시간 동안 저장된 결과를 사용한다.

@st.cache_data(ttl=3600)
def get_boxoffice(target_date):
    # Streamlit Cloud의 Secrets에서 인증키를 가져온다.
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

    # API에 요청 보내기
    response = requests.get(url, params=params, timeout=10)

    # HTTP 오류가 발생하면 예외 발생
    response.raise_for_status()

    # JSON 형태의 응답을 파이썬 자료로 변환
    return response.json()


# --------------------------------------------------
# 4. API 호출 및 오류 처리
# --------------------------------------------------

try:
    data = get_boxoffice(target_date)

except KeyError:
    st.error(
        "KOBIS 인증키를 찾을 수 없습니다.\n\n"
        "확인할 것:\n"
        "1. Streamlit Cloud의 Secrets에 KOBIS_KEY가 있는지 확인하세요.\n"
        "2. 이름이 정확히 KOBIS_KEY인지 확인하세요.\n"
        "3. 인증키 값을 따옴표 안에 올바르게 입력했는지 확인하세요."
    )
    st.stop()

except requests.exceptions.RequestException as e:
    st.error(
        "KOBIS API 요청에 실패했습니다.\n\n"
        "확인할 것:\n"
        "1. 인터넷 연결 상태를 확인하세요.\n"
        "2. KOBIS API 서버가 정상적으로 동작하는지 확인하세요.\n"
        "3. 인증키가 유효한지 확인하세요.\n\n"
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
# 5. faultInfo 확인
# --------------------------------------------------
# KOBIS는 인증키가 잘못되어도 HTTP 상태코드가 200일 수 있다.
# 따라서 faultInfo가 있는지 직접 확인해야 한다.

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
        "3. API 요청 날짜가 올바른지 확인하세요."
    )
    st.stop()


# --------------------------------------------------
# 6. 영화 목록 가져오기
# --------------------------------------------------

boxoffice_result = data.get("boxOfficeResult", {})
movie_list = boxoffice_result.get("dailyBoxOfficeList", [])


# 영화 목록이 비어 있는 경우
if not movie_list:
    st.warning(
        "조회된 영화 목록이 없습니다.\n\n"
        "확인할 것:\n"
        "1. 조회 날짜가 올바른지 확인하세요.\n"
        "2. KOBIS API에서 해당 날짜의 일별 박스오피스가 제공되는지 확인하세요.\n"
        "3. 인증키가 정상적으로 작동하는지 확인하세요.\n"
        "4. KOBIS API 응답에 오류 정보가 있는지 확인하세요."
    )
    st.stop()


# --------------------------------------------------
# 7. 숫자 데이터를 실제 숫자로 변환
# --------------------------------------------------
# KOBIS API에서는 rank, audiCnt 등의 값도 문자열로 온다.
# 그래프와 정렬에 사용할 수 있도록 int로 변환한다.

movies = []

for movie in movie_list:
    movies.append({
        "순위": int(movie["rank"]),
        "영화명": movie["movieNm"],
        "개봉일": movie["openDt"],
        "관객수": int(movie["audiCnt"]),
        "누적관객": int(movie["audiAcc"]),
        "스크린수": int(movie["scrnCnt"]),
    })


# --------------------------------------------------
# 8. 전체 영화 표 만들기
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
# 9. 1위 영화 정보
# --------------------------------------------------

first_movie = movies[0]

st.subheader("🥇 1위 영화")

st.markdown(f"### {first_movie['영화명']}")


# 지표 카드 세 개
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "어제 관객수",
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
# 10. 관객수 상위 5편 막대그래프
# --------------------------------------------------

st.subheader("📊 관객수 상위 5편")

# 관객수를 기준으로 내림차순 정렬
top5 = sorted(
    movies,
    key=lambda movie: movie["관객수"],
    reverse=True
)[:5]

# 그래프에 사용할 데이터 만들기
chart_data = {
    movie["영화명"]: movie["관객수"]
    for movie in top5
}

st.bar_chart(chart_data, y_label="관객수", x_label="영화명")
