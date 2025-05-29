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
st.set_page_config(page_title="부동산 가격 분석 AI 에이전트", page_icon="🏠")

# OpenAI API 키 가져오기
def get_api_key():
    try:
        return st.secrets["OPENAI_API_KEY"]
    except:
        return st.sidebar.text_input("OpenAI API 키를 입력하세요", type="password")

# 사이드바 설정
st.sidebar.title("설정")
api_key = get_api_key()

if api_key and api_key.startswith("sk-"):
    st.sidebar.success("✅ API 키가 설정되었습니다")
else:
    st.sidebar.warning("⚠️ API 키를 설정해주세요")

st.title("🏠 부동산 가격 분석 AI 데이터 분석가")
st.write("중앙일보의 최신 부동산 뉴스를 실시간으로 분석합니다.")

# 기본 샘플 데이터 (크롤링 실패 시 백업)
DEFAULT_ARTICLES = [
    {
        "title": "강남 아파트값 3개월 연속 상승세",
        "content": "서울 강남구 아파트 매매가격이 3개월 연속 상승세를 이어갔다. 한국부동산원에 따르면...",
        "date": "2025-01-15",
        "region": "강남",
        "price_trend": "상승",
        "url": "#",
        "source": "샘플데이터"
    }
]

# 간단한 크롤링 함수
@st.cache_data(ttl=1800)  # 30분 캐시
def simple_crawl_joongang(keyword="부동산 가격", max_articles=5):
    """중앙일보에서 간단하게 기사를 크롤링합니다."""
    try:
        encoded_keyword = urllib.parse.quote(keyword)
        url = f"https://www.joongang.co.kr/search/news?keyword={encoded_keyword}"
        
        # User-Agent 설정
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
                
                # 부동산 가격 관련 기사인지 확인
                price_keywords = ["가격", "시세", "매매", "전세", "상승", "하락"]
                if not any(kw in title or kw in summary for kw in price_keywords):
                    continue
                
                # 지역 추출
                regions = ["강남", "서초", "송파", "마포", "서울", "경기"]
                article_region = "기타"
                for region in regions:
                    if region in title or region in summary:
                        article_region = region
                        break
                
                # 가격 동향
                if any(word in title + summary for word in ["상승", "올라", "급등"]):
                    trend = "상승"
                elif any(word in title + summary for word in ["하락", "내려", "급락"]):
                    trend = "하락"
                else:
                    trend = "보합"
                
                articles.append({
                    "title": title,
                    "content": summary,
                    "date": date[:10] if len(date) > 10 else date,
                    "region": article_region,
                    "price_trend": trend,
                    "url": link,
                    "source": "중앙일보"
                })
                
            except Exception as e:
                continue
        
        return articles if articles else DEFAULT_ARTICLES
        
    except Exception as e:
        st.warning(f"크롤링 중 오류 발생: {e}")
        return DEFAULT_ARTICLES

# 검색 함수
def search_articles(query, articles):
    """기사에서 관련 내용을 검색합니다."""
    if not articles:
        return []
    
    query_lower = query.lower()
    results = []
    
    for article in articles:
        score = 0
        
        # 제목, 내용, 지역에서 키워드 매칭
        for keyword in query_lower.split():
            if keyword in article["title"].lower():
                score += 3
            if keyword in article["content"].lower():
                score += 2
            if keyword in article["region"].lower():
                score += 2
        
        if score > 0:
            results.append((score, article))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:3]]

# GPT 응답 생성
def get_gpt_response(query, articles):
    if not api_key:
        return simple_response(query, articles)
    
    try:
        client = OpenAI(api_key=api_key.strip())
        
        context = "최신 부동산 뉴스:\n\n"
        for i, article in enumerate(articles[:3]):
            context += f"{i+1}. {article['title']} ({article['date']})\n"
            context += f"   지역: {article['region']} | 동향: {article['price_trend']}\n"
            context += f"   {article['content'][:200]}...\n\n"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "부동산 전문가로서 최신 뉴스를 바탕으로 답변하세요."},
                {"role": "user", "content": f"{context}\n질문: {query}"}
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except:
        return simple_response(query, articles)

# 간단한 응답 (API 키 없을 때)
def simple_response(query, articles):
    if not articles:
        return "관련 뉴스를 찾을 수 없습니다."
    
    response = f"'{query}'에 대한 최신 뉴스:\n\n"
    for i, article in enumerate(articles[:3]):
        response += f"**{i+1}. {article['title']}**\n"
        response += f"- 날짜: {article['date']}\n"
        response += f"- 지역: {article['region']}\n"
        response += f"- 동향: {article['price_trend']}\n"
        response += f"- {article['content'][:150]}...\n\n"
    
    return response

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "articles" not in st.session_state:
    st.session_state.articles = []

# 데이터 수집 섹션
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("📰 뉴스 수집", type="primary", use_container_width=True):
        with st.spinner("중앙일보에서 최신 뉴스를 가져오는 중..."):
            articles = simple_crawl_joongang("부동산 가격", 10)
            st.session_state.articles = articles
            st.success(f"{len(articles)}개 기사 수집 완료!")

with col2:
    if st.button("🗑️ 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 수집된 기사 정보
if st.session_state.articles:
    st.sidebar.success(f"📊 {len(st.session_state.articles)}개 기사 보유")
    
    with st.sidebar.expander("수집된 기사"):
        for art in st.session_state.articles[:5]:
            st.write(f"• {art['title'][:30]}...")
            st.caption(f"{art['date']} | {art['region']}")

# 메인 채팅 인터페이스
if not st.session_state.articles:
    st.info("💡 먼저 사이드바에서 '📰 뉴스 수집' 버튼을 클릭하여 최신 뉴스를 가져오세요!")

# 대화 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 사용자 입력
if prompt := st.chat_input("질문하세요 (예: 강남 아파트 가격은?)"):
    # 사용자 메시지
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # 응답 생성
    with st.chat_message("assistant"):
        if not st.session_state.articles:
            response = "먼저 뉴스를 수집해주세요! 사이드바의 '📰 뉴스 수집' 버튼을 클릭하세요."
            st.write(response)
        else:
            with st.spinner("분석 중..."):
                # 관련 기사 검색
                relevant = search_articles(prompt, st.session_state.articles)
                
                # 응답 생성
                if relevant:
                    response = get_gpt_response(prompt, relevant)
                else:
                    response = "관련 기사를 찾을 수 없습니다. 다른 질문을 해보세요."
                
                st.write(response)
                
                # 관련 기사 링크 표시
                if relevant:
                    with st.expander("📎 관련 기사"):
                        for art in relevant[:3]:
                            if art['url'] != '#':
                                st.write(f"- [{art['title']}]({art['url']})")
                            else:
                                st.write(f"- {art['title']}")
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# 예시 질문
st.sidebar.header("💡 예시 질문")
for ex in ["강남 아파트 가격", "전세 시장 동향", "부동산 가격 전망"]:
    if st.sidebar.button(ex):
        st.rerun()
