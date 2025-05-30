# 대화형 쳇봇 애플리케이션에 필요한 라이브러리 임포트
import streamlit as st
import json
from openai import OpenAI
import re
import urllib.request
import urllib.parse
from datetime import datetime
import time
import random

# 페이지 설정
st.set_page_config(
    page_title="AI 뉴스 분석 에이전트", 
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    /* 메인 컨테이너 스타일 */
    .main {
        padding-top: 2rem;
    }
    
    /* 헤더 스타일 */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    /* 카드 스타일 */
    .news-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid #e0e0e0;
    }
    
    .news-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    /* 메트릭 카드 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* 사이드바 스타일 */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* 채팅 메시지 스타일 */
    .stChatMessage {
        background-color: #f8f9fa;
        border-radius: 15px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #4a5568;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: white;
        color: #667eea;
    }
    
    /* 정보 박스 스타일 */
    div[data-testid="stAlert"] {
        background-color: #e6f2ff;
        border: 1px solid #667eea;
        border-radius: 10px;
        color: #2d3748;
    }
    
    /* 입력 필드 스타일 */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        padding: 0.75rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 로딩 애니메이션 */
    .loading-dots {
        display: inline-flex;
        align-items: center;
    }
    
    .loading-dots span {
        height: 10px;
        width: 10px;
        background-color: #667eea;
        border-radius: 50%;
        display: inline-block;
        margin: 0 3px;
        animation: bounce 1.4s infinite ease-in-out both;
    }
    
    .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
    .loading-dots span:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes bounce {
        0%, 80%, 100% {
            transform: scale(0);
        } 40% {
            transform: scale(1.0);
        }
    }
    
    /* 그라디언트 텍스트 */
    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API 키 가져오기
def get_api_keys():
    """Streamlit secrets에서 API 키들을 가져옵니다."""
    openai_key = None
    naver_client_id = None
    naver_client_secret = None
    
    try:
        openai_key = st.secrets["OPENAI_API_KEY"]
    except:
        openai_key = st.sidebar.text_input("🔑 OpenAI API 키", type="password", help="OpenAI API 키를 입력하세요")
    
    try:
        naver_client_id = st.secrets["NAVER_CLIENT_ID"]
        naver_client_secret = st.secrets["NAVER_CLIENT_SECRET"]
    except:
        with st.sidebar.expander("🔐 네이버 API 설정"):
            naver_client_id = st.text_input("네이버 Client ID", help="네이버 개발자 센터에서 발급받은 ID")
            naver_client_secret = st.text_input("네이버 Client Secret", type="password", help="네이버 개발자 센터에서 발급받은 Secret")
    
    return openai_key, naver_client_id, naver_client_secret

# API 키 가져오기
openai_key, naver_client_id, naver_client_secret = get_api_keys()

# 사이드바 설정
st.sidebar.markdown("## ⚙️ 설정")

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

# API 상태를 더 예쁘게 표시
st.sidebar.markdown(f"""
<div style="background-color: #f0f2f6; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
    <h4 style="margin: 0; color: #2d3748;">API 연결 상태</h4>
    <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">{" | ".join(api_status)}</p>
</div>
""", unsafe_allow_html=True)

# 메인 헤더
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; font-size: 2.5rem;">📰 AI 뉴스 분석 에이전트</h1>
    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">네이버 뉴스를 실시간으로 검색하고 AI가 분석해드립니다</p>
</div>
""", unsafe_allow_html=True)

# 최신 이슈 키워드
TRENDING_TOPICS = {
    "💹 경제": ["금리", "환율", "주식", "부동산", "물가", "실업률"],
    "🏛️ 정치": ["국회", "대통령", "선거", "정당", "외교", "정책"],
    "👥 사회": ["교육", "의료", "복지", "범죄", "환경", "노동"],
    "💻 IT/과학": ["AI", "반도체", "전기차", "바이오", "우주", "메타버스"],
    "🎭 문화": ["K팝", "드라마", "영화", "스포츠", "게임", "관광"],
    "🌍 국제": ["미국", "중국", "일본", "러시아", "유럽", "중동"]
}

# 네이버 뉴스 검색 함수
@st.cache_data(ttl=1800)  # 30분 캐시
def search_naver_news(query, display=20, start=1, sort="date"):
    """네이버 뉴스 검색 API를 사용하여 뉴스를 검색합니다."""
    if not naver_client_id or not naver_client_secret:
        st.error("⚠️ 네이버 API 키가 설정되지 않았습니다!")
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
            st.error(f"❌ 네이버 API 오류: {rescode}")
            return []
            
    except Exception as e:
        st.error(f"❌ 뉴스 검색 중 오류 발생: {e}")
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
        st.markdown(f'<p class="gradient-text">🔍 관련 기사 {len(filtered)}개 발견</p>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ 직접적으로 관련된 기사를 찾지 못했습니다. 전체 기사를 바탕으로 답변합니다.")
    
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
4. 답변은 구체적이고 명확하게 하되, 추측인 경우 그렇게 표시하세요.
5. 이모지를 적절히 사용하여 읽기 쉽게 만드세요."""
        
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
        return "관련 뉴스를 찾을 수 없습니다. 😔"
    
    response = f"📰 **'{query}'에 대한 검색 결과:**\n\n"
    for i, article in enumerate(articles[:3]):
        response += f"### {i+1}. {article['title']}\n"
        response += f"📅 {article['date']} {article.get('time', '')} | 🏷️ {article.get('category', '일반')}\n\n"
        response += f"{article['content'][:200]}...\n\n"
        response += f"🔗 [기사 전문 보기]({article['url']})\n\n"
        response += "---\n\n"
    
    return response

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "articles" not in st.session_state:
    st.session_state.articles = []
if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = ""

# 뉴스 수집 섹션
st.sidebar.markdown("## 🔍 뉴스 수집")

# 검색 키워드 입력
search_keyword = st.sidebar.text_input(
    "검색 키워드", 
    placeholder="예: AI, 경제, 선거, 날씨 등",
    help="검색하고 싶은 뉴스 주제를 입력하세요"
)

# 검색 옵션
col1, col2 = st.sidebar.columns(2)
with col1:
    num_articles = st.selectbox("📊 기사 수", [10, 20, 30, 50], index=1)
with col2:
    sort_option = st.selectbox("🔄 정렬", ["date", "sim"], format_func=lambda x: "최신순" if x == "date" else "정확도순")

# 뉴스 수집 버튼
if st.sidebar.button("📰 뉴스 수집", type="primary", use_container_width=True):
    if search_keyword:
        with st.spinner(f"'{search_keyword}' 관련 뉴스를 검색 중..."):
            articles = search_naver_news(search_keyword, display=num_articles, sort=sort_option)
            if articles:
                st.session_state.articles = articles
                st.session_state.search_keyword = search_keyword
                st.success(f"✅ {len(articles)}개 기사 수집 완료!")
                st.balloons()
            else:
                st.warning("검색 결과가 없습니다. 다른 키워드를 시도해보세요.")
    else:
        st.error("검색 키워드를 입력해주세요!")

# 초기화 버튼
if st.sidebar.button("🗑️ 초기화", use_container_width=True):
    st.session_state.messages = []
    st.session_state.articles = []
    st.rerun()

# 수집된 기사 정보
if st.session_state.articles:
    st.sidebar.markdown(f"""
    <div class="metric-card" style="margin: 1rem 0;">
        <h3 style="margin: 0;">📊 검색 결과</h3>
        <p style="margin: 0.5rem 0; font-size: 1.5rem;">{len(st.session_state.articles)}개 기사</p>
        <p style="margin: 0; opacity: 0.8;">'{st.session_state.search_keyword}'</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar.expander("📋 수집된 기사 목록", expanded=False):
        for i, art in enumerate(st.session_state.articles[:10]):
            st.markdown(f"""
            <div style="padding: 0.5rem 0; border-bottom: 1px solid #e0e0e0;">
                <p style="margin: 0; font-weight: 600;">{i+1}. {art['title'][:30]}...</p>
                <p style="margin: 0; font-size: 0.85rem; color: #666;">{art['date']} | {art.get('category', '일반')}</p>
            </div>
            """, unsafe_allow_html=True)

# 최신 이슈 및 키워드
st.sidebar.markdown("## 🔥 최신 이슈")

# 카테고리별 탭
tabs = st.sidebar.tabs(list(TRENDING_TOPICS.keys()))

for i, (category, keywords) in enumerate(TRENDING_TOPICS.items()):
    with tabs[i]:
        for keyword in keywords:
            if st.button(f"🔍 {keyword}", key=f"trend_{category}_{keyword}", use_container_width=True):
                with st.spinner(f"'{keyword}' 관련 뉴스 검색 중..."):
                    articles = search_naver_news(keyword, display=20)
                    if articles:
                        st.session_state.articles = articles
                        st.session_state.search_keyword = keyword
                        st.rerun()

# 메인 채팅 인터페이스
if not st.session_state.articles:
    # 환영 메시지
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="news-card" style="text-align: center; padding: 3rem;">
            <h2 class="gradient-text">🎯 AI 뉴스 분석을 시작하세요!</h2>
            <p style="font-size: 1.1rem; color: #4a5568; margin: 1rem 0;">
                최신 뉴스를 검색하고 AI가 심층 분석해드립니다
            </p>
            
            <div style="background-color: #f7fafc; padding: 1.5rem; border-radius: 10px; margin: 2rem 0;">
                <h3 style="color: #2d3748; margin-bottom: 1rem;">📚 사용 방법</h3>
                <ol style="text-align: left; color: #4a5568;">
                    <li>사이드바에서 검색 키워드를 입력하거나</li>
                    <li>최신 이슈에서 관심 있는 키워드를 클릭하여</li>
                    <li>뉴스를 수집한 후 질문해보세요!</li>
                </ol>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-top: 2rem;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 10px;">
                    <h4 style="margin: 0;">💡 장점 1</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">다양한 언론사의 뉴스를 한 번에</p>
                </div>
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 1rem; border-radius: 10px;">
                    <h4 style="margin: 0;">💡 장점 2</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">실시간 최신 뉴스 제공</p>
                </div>
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 1rem; border-radius: 10px;">
                    <h4 style="margin: 0;">💡 장점 3</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">AI의 심층 분석</p>
                </div>
                <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; padding: 1rem; border-radius: 10px;">
                    <h4 style="margin: 0;">💡 장점 4</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">정확도순/최신순 정렬</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    # 수집된 기사 요약 정보
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; opacity: 0.8;">🔍 검색어</h4>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.8rem; font-weight: bold;">{}</p>
        </div>
        """.format(st.session_state.search_keyword), unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h4 style="margin: 0; opacity: 0.8;">📰 수집 기사</h4>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.8rem; font-weight: bold;">{}개</p>
        </div>
        """.format(len(st.session_state.articles)), unsafe_allow_html=True)
    with col3:
        latest_date = max(art['date'] for art in st.session_state.articles)
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h4 style="margin: 0; opacity: 0.8;">📅 최신 기사</h4>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.8rem; font-weight: bold;">{}</p>
        </div>
        """.format(latest_date), unsafe_allow_html=True)
    with col4:
        categories = [art.get('category', '일반') for art in st.session_state.articles]
        most_common = max(set(categories), key=categories.count)
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <h4 style="margin: 0; opacity: 0.8;">🏷️ 주요 카테고리</h4>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.5rem; font-weight: bold;">{}</p>
        </div>
        """.format(most_common), unsafe_allow_html=True)
    
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
                st.markdown(f"### {category} 관련 질문 예시:")
                cols = st.columns(len(questions))
                for i, q in enumerate(questions):
                    with cols[i]:
                        if st.button(f"💭 {q}", key=f"example_{category}_{i}", use_container_width=True):
                            st.session_state.messages.append({"role": "user", "content": q})
                            st.rerun()
                shown = True
                break
        
        if not shown:
            st.markdown("### 일반적인 질문 예시:")
            default_questions = [
                "이 주제에 대한 최신 동향은?",
                "전문가들의 의견은?",
                "향후 전망은?"
            ]
            cols = st.columns(len(default_questions))
            for i, q in enumerate(default_questions):
                with cols[i]:
                    if st.button(f"💭 {q}", key=f"example_default_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": q})
                        st.rerun()

# 대화 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력
if prompt := st.chat_input("수집된 뉴스에 대해 질문하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        if not st.session_state.articles:
            response = "먼저 뉴스를 수집해주세요! 🔍 검색 키워드를 입력하거나 최신 이슈에서 키워드를 선택하세요."
            relevant = []
        else:
            # 로딩 애니메이션
            with st.spinner("AI가 뉴스를 분석하고 있습니다..."):
                relevant = filter_articles(prompt, st.session_state.articles)
                
                if relevant:
                    response = get_gpt_response(prompt, relevant)
                else:
                    # 관련 기사가 없을 때도 전체 기사를 바탕으로 답변 시도
                    response = get_gpt_response(prompt, st.session_state.articles[:5])
                    relevant = st.session_state.articles[:5]
        
        st.markdown(response)
        
        # 관련 기사 링크 (항상 표시)
        if relevant:
            with st.expander("📎 참고한 기사", expanded=True):
                for i, art in enumerate(relevant[:3]):
                    st.markdown(f"""
                    <div class="news-card">
                        <h4 style="margin: 0; color: #2d3748;">{i+1}. <a href="{art['url']}" target="_blank" style="color: #667eea; text-decoration: none;">{art['title']}</a></h4>
                        <p style="margin: 0.5rem 0; color: #718096; font-size: 0.9rem;">
                            📅 {art['date']} {art.get('time', '')} | 🏷️ {art.get('category', '일반')}
                        </p>
                        <p style="margin: 0; color: #4a5568;">{art['content'][:150]}...</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# 하단 정보
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="background-color: #e6f2ff; padding: 1rem; border-radius: 10px;">
    <h4 style="margin: 0 0 0.5rem 0; color: #2d3748;">💡 프로 팁</h4>
    
    <h5 style="margin: 0.5rem 0; color: #4a5568;">검색 팁:</h5>
    <ul style="margin: 0; padding-left: 1.5rem; color: #4a5568;">
        <li>띄어쓰기로 여러 키워드 조합</li>
        <li>따옴표("")로 정확한 구문 검색</li>
        <li>최신순: 최근 뉴스 우선</li>
        <li>정확도순: 관련도 높은 순</li>
    </ul>
    
    <h5 style="margin: 1rem 0 0.5rem 0; color: #4a5568;">질문 팁:</h5>
    <ul style="margin: 0; padding-left: 1.5rem; color: #4a5568;">
        <li>구체적인 질문이 정확한 답변을 받습니다</li>
        <li>예: "은행들이 전세대출을 거부하나요?"</li>
        <li>예: "최근 금리 인상 영향은?"</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# 푸터
st.sidebar.markdown("""
<div style="text-align: center; margin-top: 2rem; padding: 1rem; color: #718096;">
    <p style="margin: 0;">Made with ❤️ by AI News Agent</p>
    <p style="margin: 0; font-size: 0.85rem;">Powered by OpenAI & Naver API</p>
</div>
""", unsafe_allow_html=True)
