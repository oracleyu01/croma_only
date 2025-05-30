# AI News Analysis Agent - Stable Version
import streamlit as st
import json
from openai import OpenAI
import re
import urllib.request
import urllib.parse
from datetime import datetime
import time
from collections import Counter

# 페이지 설정
st.set_page_config(
    page_title="AI News Intelligence Hub", 
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 간단한 스타일 적용
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    
    .stButton > button {
        width: 100%;
        background-color: #6366f1;
        color: white;
        border-radius: 8px;
        padding: 0.75rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background-color: #4f46e5;
    }
    
    .metric-container {
        background-color: #f3f4f6;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .news-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "articles" not in st.session_state:
    st.session_state.articles = []
if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = ""

# 카테고리 정의
CATEGORIES = {
    "💹 경제": ["경제", "금리", "환율", "주식", "부동산", "물가", "실업", "투자"],
    "🏛️ 정치": ["정치", "국회", "대통령", "선거", "정당", "외교", "정책"],
    "💻 IT/과학": ["AI", "인공지능", "반도체", "전기차", "바이오", "우주", "IT", "기술"],
    "🎭 문화": ["문화", "K팝", "드라마", "영화", "스포츠", "게임", "관광"],
    "👥 사회": ["사회", "교육", "의료", "복지", "범죄", "환경", "노동"],
    "🌍 국제": ["국제", "미국", "중국", "일본", "러시아", "유럽", "UN"]
}

# 뉴스 검색 함수
@st.cache_data(ttl=1800)
def search_naver_news(query, display=20, start=1, sort="date"):
    """네이버 뉴스 검색 API를 사용하여 뉴스를 검색합니다."""
    if not naver_client_id or not naver_client_secret:
        return []
    
    try:
        encText = urllib.parse.quote(query)
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display}&start={start}&sort={sort}"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", naver_client_id)
        request.add_header("X-Naver-Client-Secret", naver_client_secret)
        
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            result = json.loads(response_body.decode('utf-8'))
            
            articles = []
            for item in result.get('items', []):
                title = re.sub('<[^<]+?>', '', item['title'])
                description = re.sub('<[^<]+?>', '', item['description'])
                
                pub_date = datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S +0900')
                
                # 카테고리 분류
                category = categorize_article(title, description)
                
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
            return []
            
    except Exception as e:
        st.error(f"❌ 뉴스 검색 중 오류 발생: {e}")
        return []

def categorize_article(title, content):
    """기사 카테고리 자동 분류"""
    text = (title + " " + content).lower()
    
    scores = {}
    for cat, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score
    
    return max(scores, key=scores.get) if scores else "📰 일반"

def get_gpt_response(query, articles):
    """GPT를 사용하여 뉴스 분석"""
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
        
        system_prompt = """당신은 뉴스 분석 전문가입니다. 
사용자의 질문에 대해 제공된 뉴스 기사를 분석하여 명확하고 통찰력 있는 답변을 제공하세요.
답변에는 다음을 포함하세요:
1. 핵심 요약
2. 주요 트렌드나 패턴
3. 실용적인 인사이트
이모지를 적절히 사용하여 읽기 쉽게 만드세요."""
        
        user_prompt = f"{context}\n사용자 질문: {query}\n\n위 기사들을 분석하여 답변해주세요."
        
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

def simple_response(query, articles):
    """GPT 없이 간단한 응답 생성"""
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

# 헤더
st.markdown("# 🚀 AI News Intelligence Hub")
st.markdown("실시간 뉴스 수집 • AI 기반 심층 분석 • 데이터 시각화")
st.markdown("---")

# 사이드바
st.sidebar.markdown("## ⚙️ Control Center")

# API 상태 표시
api_status = []
if openai_key and openai_key.startswith("sk-"):
    api_status.append("✅ OpenAI")
else:
    api_status.append("❌ OpenAI")

if naver_client_id and naver_client_secret:
    api_status.append("✅ Naver")
else:
    api_status.append("❌ Naver")

st.sidebar.info(f"API 연결 상태: {' | '.join(api_status)}")

# 분석 모드
st.sidebar.markdown("### 🎯 분석 모드")
analysis_mode = st.sidebar.radio(
    "모드 선택",
    ["대화형 분석", "데이터 시각화", "심층 분석"]
)

# 뉴스 수집
st.sidebar.markdown("### 🔍 뉴스 수집")
search_keyword = st.sidebar.text_input(
    "검색어 입력", 
    placeholder="예: AI, 경제, 선거..."
)

col1, col2 = st.sidebar.columns(2)
with col1:
    num_articles = st.selectbox("기사 수", [20, 30, 50, 100])
with col2:
    sort_option = st.selectbox("정렬", ["date", "sim"], 
                             format_func=lambda x: "최신순" if x == "date" else "정확도순")

if st.sidebar.button("🚀 뉴스 수집", type="primary"):
    if search_keyword:
        with st.spinner("뉴스를 수집하고 있습니다..."):
            articles = search_naver_news(search_keyword, display=num_articles, sort=sort_option)
            if articles:
                st.session_state.articles = articles
                st.session_state.search_keyword = search_keyword
                st.success(f"✅ {len(articles)}개 기사 수집 완료!")
                st.balloons()
            else:
                st.warning("검색 결과가 없습니다.")
    else:
        st.error("검색어를 입력해주세요!")

# 초기화 버튼
if st.sidebar.button("🗑️ 초기화"):
    st.session_state.messages = []
    st.session_state.articles = []
    st.rerun()

# 실시간 트렌드
st.sidebar.markdown("### 🔥 실시간 트렌드")
trending_keywords = ["삼성전자", "테슬라", "AI", "부동산", "금리", "우크라이나", "K팝"]
for keyword in trending_keywords:
    if st.sidebar.button(f"🔍 {keyword}", key=f"trend_{keyword}"):
        with st.spinner(f"'{keyword}' 검색 중..."):
            articles = search_naver_news(keyword, display=20)
            if articles:
                st.session_state.articles = articles
                st.session_state.search_keyword = keyword
                st.rerun()

# 메인 컨텐츠
if not st.session_state.articles:
    # 환영 화면
    st.markdown("""
    ## 🎯 뉴스 인텔리전스 시작하기
    
    AI가 실시간 뉴스를 분석하여 인사이트를 제공합니다.
    
    ### 📚 사용 방법
    1. 사이드바에서 검색어를 입력하거나
    2. 실시간 트렌드에서 키워드를 선택하여
    3. 뉴스를 수집한 후 질문해보세요!
    
    ### 💡 주요 기능
    - 🔍 **스마트 검색**: 키워드 기반 정밀 검색
    - 🤖 **AI 분석**: GPT 기반 심층 분석
    - 📊 **데이터 시각화**: 통계 및 트렌드 분석
    """)
else:
    # 통계 표시
    if st.session_state.articles:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🔍 검색어", st.session_state.search_keyword)
        
        with col2:
            st.metric("📰 기사 수", f"{len(st.session_state.articles)}개")
        
        with col3:
            latest_date = max(art['date'] for art in st.session_state.articles)
            st.metric("📅 최신 기사", latest_date)
        
        with col4:
            categories = [art.get('category', '일반') for art in st.session_state.articles]
            most_common = max(set(categories), key=categories.count)
            st.metric("🏷️ 주요 카테고리", most_common)
    
    st.markdown("---")
    
    if analysis_mode == "대화형 분석":
        # 대화형 분석 모드
        st.markdown("## 💬 대화형 분석")
        
        # 예시 질문 버튼들
        st.markdown("### 💡 빠른 질문하기")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📈 이 주제의 최신 동향은?", use_container_width=True):
                question = "이 주제에 대한 최신 동향은 무엇인가요?"
                st.session_state.messages.append({"role": "user", "content": question})
                with st.spinner("AI가 분석 중입니다..."):
                    response = get_gpt_response(question, st.session_state.articles)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()
                
            if st.button("💭 전문가들의 의견은?", use_container_width=True):
                question = "이 주제에 대한 전문가들의 의견은 어떤가요?"
                st.session_state.messages.append({"role": "user", "content": question})
                with st.spinner("AI가 분석 중입니다..."):
                    response = get_gpt_response(question, st.session_state.articles)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()
        
        with col2:
            if st.button("🔮 향후 전망은?", use_container_width=True):
                question = "이 주제의 향후 전망은 어떻게 되나요?"
                st.session_state.messages.append({"role": "user", "content": question})
                with st.spinner("AI가 분석 중입니다..."):
                    response = get_gpt_response(question, st.session_state.articles)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()
                
            if st.button("⚡ 주요 이슈는?", use_container_width=True):
                question = "현재 가장 중요한 이슈는 무엇인가요?"
                st.session_state.messages.append({"role": "user", "content": question})
                with st.spinner("AI가 분석 중입니다..."):
                    response = get_gpt_response(question, st.session_state.articles)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()
        
        st.markdown("---")
        
        # 대화 표시
        if st.session_state.messages:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
                    # assistant 메시지일 때 관련 기사 표시
                    if msg["role"] == "assistant" and st.session_state.articles:
                        with st.expander("📎 참고 기사", expanded=False):
                            for i, art in enumerate(st.session_state.articles[:3]):
                                st.markdown(f"**{i+1}. [{art['title']}]({art['url']})**")
                                st.caption(f"{art['date']} | {art.get('category', '일반')}")
                                st.write(art['content'][:150] + "...")
                                if i < 2:
                                    st.markdown("---")
        
        # 사용자 입력
        if prompt := st.chat_input("뉴스에 대해 질문하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("AI가 분석 중입니다..."):
                    response = get_gpt_response(prompt, st.session_state.articles)
                st.markdown(response)
                
                # 관련 기사 표시
                with st.expander("📎 참고 기사", expanded=False):
                    for i, art in enumerate(st.session_state.articles[:3]):
                        st.markdown(f"**{i+1}. [{art['title']}]({art['url']})**")
                        st.caption(f"{art['date']} | {art.get('category', '일반')}")
                        st.write(art['content'][:150] + "...")
                        if i < 2:
                            st.markdown("---")
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    elif analysis_mode == "데이터 시각화":
        # 데이터 시각화 모드
        st.markdown("## 📊 데이터 시각화")
        
        # 카테고리 분포
        categories = [art.get('category', '일반') for art in st.session_state.articles]
        cat_counts = Counter(categories)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 카테고리별 분포")
            chart_data = {
                "카테고리": list(cat_counts.keys()),
                "기사 수": list(cat_counts.values())
            }
            st.bar_chart(data=chart_data, x="카테고리", y="기사 수", height=400)
        
        with col2:
            st.markdown("### 📅 날짜별 분포")
            dates = [art['date'] for art in st.session_state.articles]
            date_counts = Counter(dates)
            
            date_data = {
                "날짜": sorted(date_counts.keys()),
                "기사 수": [date_counts[d] for d in sorted(date_counts.keys())]
            }
            st.line_chart(data=date_data, x="날짜", y="기사 수", height=400)
        
        # 주요 키워드
        st.markdown("### ☁️ 주요 키워드")
        all_text = " ".join([art['title'] + " " + art['content'] for art in st.session_state.articles])
        words = all_text.split()
        
        # 불용어 제거
        stopwords = ['의', '가', '이', '은', '들', '는', '좀', '잘', '과', '를', '으로', '자', '에', '한', '하다']
        words = [w for w in words if len(w) > 1 and w not in stopwords]
        
        word_freq = Counter(words)
        top_words = word_freq.most_common(20)
        
        # 워드 클라우드 스타일로 표시
        word_html = ""
        for word, freq in top_words:
            size = min(2.5, 0.8 + (freq / top_words[0][1]) * 1.7)
            word_html += f'<span style="font-size: {size}rem; margin: 0.5rem; display: inline-block; color: #6366f1;">{word}</span>'
        
        st.markdown(word_html, unsafe_allow_html=True)
    
    else:
        # 심층 분석 모드
        st.markdown("## 🔍 심층 분석")
        
        analysis_type = st.selectbox(
            "분석 유형 선택",
            ["종합 분석", "트렌드 분석", "감정 분석", "예측 분석"]
        )
        
        if st.button("🚀 분석 실행", type="primary"):
            with st.spinner("심층 분석을 진행하고 있습니다..."):
                analysis = get_gpt_response(
                    f"{analysis_type}: {st.session_state.search_keyword}",
                    st.session_state.articles
                )
                st.markdown(analysis)
        
        # 기사 목록
        st.markdown("### 📰 전체 기사 목록")
        for i, art in enumerate(st.session_state.articles):
            with st.expander(f"{i+1}. {art['title']}", expanded=False):
                st.caption(f"📅 {art['date']} {art.get('time', '')} | 🏷️ {art.get('category', '일반')}")
                st.write(art['content'])
                st.markdown(f"🔗 [기사 원문]({art['url']})")

# 푸터
st.markdown("---")
st.markdown("Made with ❤️ by AI News Intelligence Hub | Powered by OpenAI & Naver API")
