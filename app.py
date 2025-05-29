# 대화형 쳇봇 애플리케이션에 필요한 라이브러리 임포트
import streamlit as st
import json
from openai import OpenAI
import re
import urllib.request
import urllib.parse
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(page_title="AI 뉴스 분석 에이전트", page_icon="📰")

# API 키 가져오기
def get_api_keys():
    """Streamlit secrets에서 API 키들을 가져옵니다."""
    openai_key = None
    naver_client_id = None
    naver_client_secret = None
    
    try:
        openai_key = st.secrets["OPENAI_API_KEY"]
    except:
        openai_key = st.sidebar.text_input("OpenAI API 키", type="password")
    
    try:
        naver_client_id = st.secrets["NAVER_CLIENT_ID"]
        naver_client_secret = st.secrets["NAVER_CLIENT_SECRET"]
    except:
        with st.sidebar.expander("네이버 API 설정"):
            naver_client_id = st.text_input("네이버 Client ID")
            naver_client_secret = st.text_input("네이버 Client Secret", type="password")
    
    return openai_key, naver_client_id, naver_client_secret

# API 키 가져오기
openai_key, naver_client_id, naver_client_secret = get_api_keys()

# 사이드바 설정
st.sidebar.title("⚙️ 설정")

# API 키 상태 표시
api_status = []
if openai_key and openai_key.startswith("sk-"):
    api_status.append("✅ OpenAI")
else:
    api_status.append("❌ OpenAI")

if naver_client_id and naver_client_secret:
    api_status.append("✅ 네이버")
else:
    api_status.append("❌ 네이버")

st.sidebar.info("API 상태: " + " | ".join(api_status))

st.title("📰 AI 뉴스 분석 에이전트")
st.write("네이버 뉴스를 실시간으로 검색하고 분석합니다.")

# 최신 이슈 키워드
TRENDING_TOPICS = {
    "경제": ["금리", "환율", "주식", "부동산", "물가", "실업률"],
    "정치": ["국회", "대통령", "선거", "정당", "외교", "정책"],
    "사회": ["교육", "의료", "복지", "범죄", "환경", "노동"],
    "IT/과학": ["AI", "반도체", "전기차", "바이오", "우주", "메타버스"],
    "문화": ["K팝", "드라마", "영화", "스포츠", "게임", "관광"],
    "국제": ["미국", "중국", "일본", "러시아", "유럽", "중동"]
}

# 네이버 뉴스 검색 함수
@st.cache_data(ttl=1800)  # 30분 캐시
def search_naver_news(query, display=20, start=1, sort="date"):
    """네이버 뉴스 검색 API를 사용하여 뉴스를 검색합니다."""
    if not naver_client_id or not naver_client_secret:
        st.error("네이버 API 키가 설정되지 않았습니다!")
        return []
    
    try:
        # API URL 설정
        encText = urllib.parse.quote(query)
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display}&start={start}&sort={sort}"
        
        # 요청 헤더 설정
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", naver_client_id)
        request.add_header("X-Naver-Client-Secret", naver_client_secret)
        
        # API 호출
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            result = json.loads(response_body.decode('utf-8'))
            
            articles = []
            for item in result.get('items', []):
                # HTML 태그 제거
                title = re.sub('<[^<]+?>', '', item['title'])
                description = re.sub('<[^<]+?>', '', item['description'])
                
                # 날짜 형식 변환
                pub_date = datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S +0900')
                
                # 카테고리 추출
                category = "일반"
                for cat, keywords in TRENDING_TOPICS.items():
                    if any(kw in title or kw in description for kw in keywords):
                        category = cat
                        break
                
                articles.append({
                    "title": title,
                    "content": description,
                    "date": pub_date.strftime("%Y-%m-%d"),
                    "time": pub_date.strftime("%H:%M"),
                    "category": category,
                    "url": item['link'],
                    "source": item.get('originallink', item['link'])
                })
            
            return articles
        else:
            st.error(f"네이버 API 오류: {rescode}")
            return []
            
    except Exception as e:
        st.error(f"뉴스 검색 중 오류 발생: {e}")
        return []

# 기사 필터링 및 검색
def filter_articles(query, articles):
    """사용자 쿼리에 맞는 기사를 필터링합니다."""
    if not articles:
        return []
    
    query_lower = query.lower()
    results = []
    
    for article in articles:
        score = 0
        
        # 키워드 매칭
        for keyword in query_lower.split():
            if keyword in article["title"].lower():
                score += 5
            if keyword in article["content"].lower():
                score += 3
            if keyword in article.get("category", "").lower():
                score += 2
        
        if score > 0:
            results.append((score, article))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:5]]

# GPT 응답 생성
def get_gpt_response(query, articles):
    if not openai_key:
        return simple_response(query, articles)
    
    try:
        client = OpenAI(api_key=openai_key.strip())
        
        context = "관련 뉴스 기사:\n\n"
        for i, article in enumerate(articles[:5]):
            context += f"[기사 {i+1}]\n"
            context += f"제목: {article['title']}\n"
            context += f"날짜: {article['date']} {article.get('time', '')}\n"
            context += f"카테고리: {article.get('category', '일반')}\n"
            context += f"내용: {article['content']}\n"
            context += f"출처: {article['source']}\n\n"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 뉴스 분석 전문가입니다. 제공된 뉴스 기사를 바탕으로 정확하고 통찰력 있는 답변을 제공하세요."},
                {"role": "user", "content": f"{context}\n질문: {query}"}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return simple_response(query, articles)

# 간단한 응답
def simple_response(query, articles):
    if not articles:
        return "관련 뉴스를 찾을 수 없습니다."
    
    response = f"📰 '{query}'에 대한 검색 결과:\n\n"
    for i, article in enumerate(articles[:3]):
        response += f"**{i+1}. {article['title']}**\n"
        response += f"- 📅 {article['date']} {article.get('time', '')} | 🏷️ {article.get('category', '일반')}\n"
        response += f"- {article['content'][:200]}...\n"
        response += f"- 🔗 [기사 보기]({article['url']})\n\n"
    
    return response

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "articles" not in st.session_state:
    st.session_state.articles = []
if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = ""

# 뉴스 수집 섹션
st.sidebar.header("🔍 뉴스 수집")

# 검색 키워드 입력
search_keyword = st.sidebar.text_input(
    "검색 키워드", 
    placeholder="예: AI, 경제, 선거, 날씨 등",
    help="검색하고 싶은 뉴스 주제를 입력하세요"
)

# 검색 옵션
col1, col2 = st.sidebar.columns(2)
with col1:
    num_articles = st.selectbox("기사 수", [10, 20, 30, 50], index=1)
with col2:
    sort_option = st.selectbox("정렬", ["date", "sim"], format_func=lambda x: "최신순" if x == "date" else "정확도순")

# 뉴스 수집 버튼
if st.sidebar.button("📰 뉴스 수집", type="primary", use_container_width=True):
    if search_keyword:
        with st.spinner(f"'{search_keyword}' 관련 뉴스를 검색 중..."):
            articles = search_naver_news(search_keyword, display=num_articles, sort=sort_option)
            if articles:
                st.session_state.articles = articles
                st.session_state.search_keyword = search_keyword
                st.success(f"✅ {len(articles)}개 기사 수집 완료!")
            else:
                st.warning("검색 결과가 없습니다.")
    else:
        st.error("검색 키워드를 입력해주세요!")

# 초기화 버튼
if st.sidebar.button("🗑️ 초기화", use_container_width=True):
    st.session_state.messages = []
    st.session_state.articles = []
    st.rerun()

# 수집된 기사 정보
if st.session_state.articles:
    st.sidebar.success(f"📊 '{st.session_state.search_keyword}' 검색 결과: {len(st.session_state.articles)}개")
    
    with st.sidebar.expander("📋 수집된 기사 목록"):
        for i, art in enumerate(st.session_state.articles[:10]):
            st.write(f"{i+1}. {art['title'][:30]}...")
            st.caption(f"{art['date']} | {art.get('category', '일반')}")

# 최신 이슈 및 키워드
st.sidebar.header("🔥 최신 이슈")

# 카테고리별 탭
tabs = st.sidebar.tabs(list(TRENDING_TOPICS.keys()))

for i, (category, keywords) in enumerate(TRENDING_TOPICS.items()):
    with tabs[i]:
        for keyword in keywords:
            if st.button(keyword, key=f"trend_{category}_{keyword}", use_container_width=True):
                with st.spinner(f"'{keyword}' 관련 뉴스 검색 중..."):
                    articles = search_naver_news(keyword, display=20)
                    if articles:
                        st.session_state.articles = articles
                        st.session_state.search_keyword = keyword
                        st.rerun()

# 메인 채팅 인터페이스
if not st.session_state.articles:
    st.info("""
    🎯 **사용 방법:**
    1. 사이드바에서 검색 키워드를 입력하거나
    2. 최신 이슈에서 관심 있는 키워드를 클릭하여
    3. 뉴스를 수집한 후 질문해보세요!
    
    💡 **네이버 뉴스 검색의 장점:**
    - 다양한 언론사의 뉴스를 한 번에 검색
    - 실시간 최신 뉴스 제공
    - 정확도순/최신순 정렬 옵션
    """)
else:
    # 수집된 기사 요약 정보
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("검색어", st.session_state.search_keyword)
    with col2:
        st.metric("수집 기사", f"{len(st.session_state.articles)}개")
    with col3:
        latest_date = max(art['date'] for art in st.session_state.articles)
        st.metric("최신 기사", latest_date)

# 대화 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 사용자 입력
if prompt := st.chat_input("수집된 뉴스에 대해 질문하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        if not st.session_state.articles:
            response = "먼저 뉴스를 수집해주세요! 검색 키워드를 입력하거나 최신 이슈에서 키워드를 선택하세요."
        else:
            with st.spinner("분석 중..."):
                relevant = filter_articles(prompt, st.session_state.articles)
                
                if relevant:
                    response = get_gpt_response(prompt, relevant)
                else:
                    response = f"'{prompt}'와 관련된 기사를 찾을 수 없습니다. 현재 '{st.session_state.search_keyword}' 관련 기사를 보유하고 있습니다."
        
        st.write(response)
        
        # 관련 기사 링크
        if st.session_state.articles and relevant:
            with st.expander("📎 참고 기사"):
                for art in relevant[:3]:
                    st.write(f"**[{art['title']}]({art['url']})**")
                    st.caption(f"{art['date']} {art.get('time', '')} | {art.get('category', '일반')}")
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# 하단 정보
st.sidebar.markdown("---")
st.sidebar.info("""
**💡 검색 팁:**
- 띄어쓰기로 여러 키워드 조합 가능
- 따옴표("")로 정확한 구문 검색
- 최신순: 최근 뉴스 우선
- 정확도순: 검색어와 관련도 높은 순
""")
