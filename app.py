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

# 기사 필터링 및 검색 (개선된 버전)
def filter_articles(query, articles):
    """사용자 쿼리에 맞는 기사를 더 정확하게 필터링합니다."""
    if not articles:
        return []
    
    # 쿼리 분석
    query_lower = query.lower()
    
    # 전문 용어 매핑 (사용자가 쓸 수 있는 표현들)
    term_mapping = {
        "녹지": ["거부", "거절", "부정적", "어려움", "까다로운", "제한"],
        "전세대출": ["전세자금대출", "전세대출", "전세 대출", "전세자금"],
        "은행": ["은행", "금융기관", "시중은행", "금융권"]
    }
    
    results = []
    
    for article in articles:
        score = 0
        title_content = (article["title"] + " " + article["content"]).lower()
        
        # 직접 키워드 매칭
        for keyword in query_lower.split():
            if keyword in title_content:
                score += 3
        
        # 전문 용어 매핑을 통한 매칭
        for user_term, related_terms in term_mapping.items():
            if user_term in query_lower:
                for related in related_terms:
                    if related in title_content:
                        score += 2
        
        # 특별히 전세대출 관련 기사에 가중치
        if "전세" in title_content and "대출" in title_content:
            score += 5
        
        if score > 0:
            results.append((score, article))
    
    results.sort(key=lambda x: x[0], reverse=True)
    filtered = [r[1] for r in results[:5]]
    
    # 디버깅 정보 출력
    if filtered:
        st.write(f"🔍 관련 기사 {len(filtered)}개 발견")
    else:
        st.write("⚠️ 직접적으로 관련된 기사를 찾지 못했습니다. 전체 기사를 바탕으로 답변합니다.")
    
    return filtered if filtered else articles[:5]

# GPT 응답 생성 (개선된 버전)
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
            context += f"내용: {article['content']}\n"
            context += f"출처: {article['source']}\n\n"
        
        # 개선된 시스템 프롬프트
        system_prompt = """당신은 뉴스 분석 전문가입니다. 사용자의 질문에 대해:
1. 제공된 뉴스 기사에서 직접적으로 관련된 내용을 찾아 답변하세요.
2. 만약 직접적인 답변이 없다면, 관련된 정보를 종합해서 추론하세요.
3. "녹지" = 부정적/거부, "전세대출" = 전세자금대출 등 금융 용어를 이해하고 답변하세요.
4. 답변은 구체적이고 명확하게 하되, 추측인 경우 그렇게 표시하세요."""
        
        user_prompt = f"{context}\n사용자 질문: {query}\n\n위 기사들을 분석하여 질문에 대해 구체적으로 답변해주세요. 특히 질문의 핵심에 집중하여 답변하세요."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
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
    
    # 예시 질문 표시
    with st.expander("💬 예시 질문", expanded=False):
        example_questions = {
            "대출": [
                "은행들이 전세대출에 대해 부정적인가요?",
                "최근 대출 금리 동향은 어떤가요?",
                "정부의 대출 규제 정책은 무엇인가요?"
            ],
            "경제": [
                "최근 경제 성장률은 어떻게 되나요?",
                "환율이 경제에 미치는 영향은?",
                "물가 상승의 주요 원인은?"
            ],
            "부동산": [
                "최근 아파트 가격 동향은?",
                "전세 시장의 변화는 어떤가요?",
                "부동산 정책의 효과는?"
            ]
        }
        
        # 현재 검색어와 관련된 예시 질문 표시
        current_keyword = st.session_state.search_keyword.lower()
        shown = False
        
        for category, questions in example_questions.items():
            if category in current_keyword or current_keyword in category:
                st.write(f"**{category} 관련 질문 예시:**")
                for q in questions:
                    st.write(f"• {q}")
                shown = True
                break
        
        if not shown:
            st.write("**일반적인 질문 예시:**")
            st.write("• 이 주제에 대한 최신 동향은 무엇인가요?")
            st.write("• 전문가들의 의견은 어떤가요?")
            st.write("• 향후 전망은 어떻게 되나요?")

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
            relevant = []
        else:
            with st.spinner("분석 중..."):
                relevant = filter_articles(prompt, st.session_state.articles)
                
                if relevant:
                    response = get_gpt_response(prompt, relevant)
                else:
                    # 관련 기사가 없을 때도 전체 기사를 바탕으로 답변 시도
                    response = get_gpt_response(prompt, st.session_state.articles[:5])
                    relevant = st.session_state.articles[:5]
        
        st.write(response)
        
        # 관련 기사 링크 (항상 표시)
        if relevant:
            with st.expander("📎 참고한 기사", expanded=True):
                for i, art in enumerate(relevant[:3]):
                    st.write(f"**{i+1}. [{art['title']}]({art['url']})**")
                    st.caption(f"📅 {art['date']} {art.get('time', '')} | {art['content'][:100]}...")
                    if i < len(relevant) - 1:
                        st.markdown("---")
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# 하단 정보
st.sidebar.markdown("---")
st.sidebar.info("""
**💡 검색 팁:**
- 띄어쓰기로 여러 키워드 조합 가능
- 따옴표("")로 정확한 구문 검색
- 최신순: 최근 뉴스 우선
- 정확도순: 검색어와 관련도 높은 순

**🎯 질문 팁:**
- 구체적인 질문이 더 정확한 답변을 받습니다
- 예: "은행들이 전세대출을 거부하나요?"
- 예: "최근 금리 인상 영향은?"
""")
