# 대화형 쳇봇 애플리케이션에 필요한 라이브러리 임포트
import streamlit as st
import json
from openai import OpenAI
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(page_title="AI 뉴스 분석 에이전트", page_icon="📰")

# OpenAI API 키 가져오기
def get_api_key():
    try:
        return st.secrets["OPENAI_API_KEY"]
    except:
        return st.sidebar.text_input("OpenAI API 키를 입력하세요", type="password")

# 사이드바 설정
st.sidebar.title("⚙️ 설정")
api_key = get_api_key()

if api_key and api_key.startswith("sk-"):
    st.sidebar.success("✅ API 키가 설정되었습니다")
else:
    st.sidebar.warning("⚠️ API 키를 설정해주세요")

st.title("📰 AI 뉴스 분석 에이전트")
st.write("중앙일보의 최신 뉴스를 실시간으로 검색하고 분석합니다.")

# 최신 이슈 키워드 (주기적으로 업데이트 필요)
TRENDING_TOPICS = {
    "경제": ["금리", "환율", "주식", "부동산", "물가", "실업률"],
    "정치": ["국회", "대통령", "선거", "정당", "외교", "정책"],
    "사회": ["교육", "의료", "복지", "범죄", "환경", "노동"],
    "IT/과학": ["AI", "반도체", "전기차", "바이오", "우주", "메타버스"],
    "문화": ["K팝", "드라마", "영화", "스포츠", "게임", "관광"],
    "국제": ["미국", "중국", "일본", "러시아", "유럽", "중동"]
}

# 크롤링 함수
@st.cache_data(ttl=1800)  # 30분 캐시
def crawl_joongang_news(keyword="최신 뉴스", max_articles=10):
    """중앙일보에서 키워드로 뉴스를 검색합니다."""
    try:
        encoded_keyword = urllib.parse.quote(keyword)
        url = f"https://www.joongang.co.kr/search/news?keyword={encoded_keyword}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request, timeout=10)
        html = response.read().decode('utf-8')
        
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        # 기사 카드 찾기
        article_cards = soup.select('div.card_body')[:max_articles]
        
        for card in article_cards:
            try:
                # 제목과 링크
                title_elem = card.select_one('h2.headline a')
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                link = title_elem.get('href', '#')
                
                # 날짜
                date_elem = card.select_one('p.date')
                date = date_elem.text.strip() if date_elem else datetime.now().strftime("%Y-%m-%d")
                
                # 요약
                summary_elem = card.select_one('p.description')
                summary = summary_elem.text.strip() if summary_elem else title
                
                # 카테고리 추출
                category = "일반"
                for cat, keywords in TRENDING_TOPICS.items():
                    if any(kw in title or kw in summary for kw in keywords):
                        category = cat
                        break
                
                articles.append({
                    "title": title,
                    "content": summary,
                    "date": date[:10] if len(date) > 10 else date,
                    "category": category,
                    "url": link,
                    "source": "중앙일보"
                })
                
            except Exception as e:
                continue
        
        return articles
        
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {e}")
        return []

# 검색 함수
def search_articles(query, articles):
    """기사에서 관련 내용을 검색합니다."""
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
    if not api_key:
        return simple_response(query, articles)
    
    try:
        client = OpenAI(api_key=api_key.strip())
        
        context = "관련 뉴스 기사:\n\n"
        for i, article in enumerate(articles[:5]):
            context += f"[기사 {i+1}]\n"
            context += f"제목: {article['title']}\n"
            context += f"날짜: {article['date']}\n"
            context += f"카테고리: {article.get('category', '일반')}\n"
            context += f"내용: {article['content']}\n\n"
        
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
        response += f"- 📅 {article['date']} | 🏷️ {article.get('category', '일반')}\n"
        response += f"- {article['content'][:150]}...\n\n"
    
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

# 기사 수 설정
num_articles = st.sidebar.slider("수집할 기사 수", 5, 20, 10)

# 뉴스 수집 버튼
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("📰 뉴스 수집", type="primary", use_container_width=True):
        if search_keyword:
            with st.spinner(f"'{search_keyword}' 관련 뉴스를 검색 중..."):
                articles = crawl_joongang_news(search_keyword, num_articles)
                if articles:
                    st.session_state.articles = articles
                    st.session_state.search_keyword = search_keyword
                    st.success(f"✅ {len(articles)}개 기사 수집 완료!")
                else:
                    st.warning("검색 결과가 없습니다.")
        else:
            st.error("검색 키워드를 입력해주세요!")

with col2:
    if st.button("🗑️ 초기화", use_container_width=True):
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
        st.write(f"**{category} 관련 키워드:**")
        # 키워드 버튼들
        for keyword in keywords:
            if st.button(keyword, key=f"trend_{category}_{keyword}", use_container_width=True):
                # 검색 키워드 설정 후 뉴스 수집
                with st.spinner(f"'{keyword}' 관련 뉴스 검색 중..."):
                    articles = crawl_joongang_news(keyword, 10)
                    if articles:
                        st.session_state.articles = articles
                        st.session_state.search_keyword = keyword
                        st.rerun()

# 메인 채팅 인터페이스
if not st.session_state.articles:
    # 환영 메시지
    st.info("""
    🎯 **사용 방법:**
    1. 사이드바에서 검색 키워드를 입력하거나
    2. 최신 이슈에서 관심 있는 키워드를 클릭하여
    3. 뉴스를 수집한 후 질문해보세요!
    
    💡 **검색 가능한 주제:** 정치, 경제, 사회, IT, 문화, 스포츠 등 모든 분야
    """)
else:
    st.success(f"📰 '{st.session_state.search_keyword}' 관련 {len(st.session_state.articles)}개 기사를 분석할 준비가 되었습니다!")

# 대화 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 사용자 입력
if prompt := st.chat_input("수집된 뉴스에 대해 질문하세요"):
    # 사용자 메시지
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # 응답 생성
    with st.chat_message("assistant"):
        if not st.session_state.articles:
            response = "먼저 뉴스를 수집해주세요! 검색 키워드를 입력하거나 최신 이슈에서 키워드를 선택하세요."
            st.write(response)
        else:
            with st.spinner("분석 중..."):
                relevant = search_articles(prompt, st.session_state.articles)
                
                if relevant:
                    response = get_gpt_response(prompt, relevant)
                else:
                    response = f"'{prompt}'와 관련된 기사를 찾을 수 없습니다. '{st.session_state.search_keyword}' 관련 다른 질문을 해보세요."
                
                st.write(response)
                
                # 관련 기사 링크
                if relevant:
                    with st.expander("📎 참고 기사"):
                        for art in relevant[:3]:
                            if art['url'] != '#':
                                st.write(f"- [{art['title']}]({art['url']})")
                            else:
                                st.write(f"- {art['title']}")
                            st.caption(f"  {art['date']} | {art.get('category', '일반')}")
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# 하단 정보
st.sidebar.markdown("---")
st.sidebar.info("""
**💡 팁:**
- 구체적인 키워드로 검색하면 더 정확한 결과를 얻을 수 있습니다
- 여러 키워드를 조합해보세요 (예: "AI 규제", "경제 전망")
- 수집된 뉴스를 바탕으로 심층 분석을 요청할 수 있습니다
""")
