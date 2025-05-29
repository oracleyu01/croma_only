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
import os

# 페이지 설정
st.set_page_config(page_title="부동산 가격 분석 AI 에이전트", page_icon="🏠")

# OpenAI API 키 가져오기
def get_api_key():
    """Streamlit secrets 또는 사이드바 입력에서 API 키 가져오기"""
    try:
        return st.secrets["OPENAI_API_KEY"]
    except:
        return st.sidebar.text_input(
            "OpenAI API 키를 입력하세요", 
            type="password",
            help="Streamlit Cloud에서는 Settings > Secrets에서 OPENAI_API_KEY를 설정하세요"
        )

# 사이드바 설정
st.sidebar.title("설정")
api_key = get_api_key()

# API 키 상태 표시
if api_key and api_key.startswith("sk-"):
    st.sidebar.success("✅ API 키가 설정되었습니다")
else:
    st.sidebar.warning("⚠️ API 키를 설정해주세요")

# 페이지 제목
st.title("🏠 부동산 가격 분석 AI 데이터 분석가")
st.write("중앙일보의 최신 부동산 뉴스를 실시간으로 분석합니다.")

# 크롤링 함수들
@st.cache_data(ttl=3600)  # 1시간 캐시
def get_article_details_url(keyword, num_pages=2):
    """중앙일보에서 키워드로 기사 URL 목록을 가져옵니다."""
    encoded_keyword = urllib.parse.quote(keyword)
    article_urls = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for page in range(1, num_pages + 1):
        list_url = f"https://www.joongang.co.kr/search/news?keyword={encoded_keyword}&page={page}"
        try:
            status_text.text(f"페이지 {page}/{num_pages} 검색 중...")
            request = urllib.request.Request(list_url)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            response = urllib.request.urlopen(request).read().decode("utf-8")
            soup = BeautifulSoup(response, "html.parser")

            # 상세 기사 링크 추출
            for headline in soup.select("div.card_body > h2.headline > a"):
                article_url = headline.get("href")
                if article_url:
                    article_urls.append(article_url)

            progress_bar.progress(page / num_pages)
            time.sleep(0.5)  # 서버 부담 감소

        except Exception as e:
            st.warning(f"페이지 {page} 스크래핑 중 오류 발생: {e}")

    progress_bar.empty()
    status_text.empty()
    return article_urls[:10]  # 최대 10개 기사만 반환

def is_price_related_article(title, content):
    """기사가 부동산 가격과 관련이 있는지 확인합니다."""
    price_keywords = [
        "가격", "시세", "매매", "전세", "월세", "상승", "하락", "거래", 
        "급등", "급락", "매매가", "전셋값", "집값", "아파트값"
    ]
    
    if any(keyword in title for keyword in price_keywords):
        return True
    
    content_preview = content[:1000] if content else ""
    if any(keyword in content_preview for keyword in price_keywords):
        if re.search(r'\d+\s*억|\d+\s*천\s*만|\d+\s*만', content_preview):
            return True
    
    return False

@st.cache_data(ttl=3600)
def extract_article_content(url):
    """URL에서 기사의 상세 내용을 추출합니다."""
    try:
        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        response = urllib.request.urlopen(request).read().decode('utf-8')
        soup = BeautifulSoup(response, 'html.parser')

        # 기사 제목 추출
        title_element = soup.select_one("h1.headline, h2.headline")
        title = title_element.text.strip() if title_element else "제목 없음"

        # 날짜 추출
        date_element = soup.select_one("time")
        date = date_element['datetime'][:10] if date_element and 'datetime' in date_element.attrs else datetime.now().strftime("%Y-%m-%d")

        # 본문 추출
        content_elements = soup.select('div.article_body p, article.article p')
        content = "\n".join([p.text.strip() for p in content_elements])
        
        if not content:  # 다른 선택자 시도
            content_elements = soup.select('div.article_body, div#article_body')
            content = content_elements[0].text.strip() if content_elements else ""

        # 부동산 가격과 관련된 기사인지 확인
        if not is_price_related_article(title, content):
            return None

        # 지역 정보 추출
        regions = ["강남", "강북", "서초", "송파", "마포", "용산", "강동", "노원", "분당", "일산", "서울", "경기"]
        article_region = "기타"
        for region in regions:
            if region in title or region in content[:500]:
                article_region = region
                break

        # 가격 동향 분석
        price_trend = "기타"
        if re.search(r'(상승|올랐|증가|오름세|급등)', content[:500]):
            price_trend = "상승"
        elif re.search(r'(하락|떨어졌|감소|내림세|급락)', content[:500]):
            price_trend = "하락"
        elif re.search(r'(유지|보합|변동없|안정)', content[:500]):
            price_trend = "안정"

        return {
            "title": title,
            "content": content[:2000],  # 처음 2000자만 저장
            "url": url,
            "date": date,
            "region": article_region,
            "price_trend": price_trend,
            "source": "중앙일보"
        }

    except Exception as e:
        st.warning(f"기사 추출 중 오류 발생: {e}")
        return None

# 데이터 수집 함수
def collect_real_estate_news(keyword="부동산 가격", num_pages=2):
    """실시간으로 중앙일보 부동산 뉴스를 수집합니다."""
    with st.spinner(f"'{keyword}' 관련 최신 뉴스를 검색하고 있습니다..."):
        # URL 수집
        article_urls = get_article_details_url(keyword, num_pages)
        
        if not article_urls:
            st.warning("검색 결과가 없습니다.")
            return []
        
        # 기사 내용 추출
        articles = []
        progress_bar = st.progress(0)
        
        for i, url in enumerate(article_urls):
            article_data = extract_article_content(url)
            if article_data:
                articles.append(article_data)
            
            progress_bar.progress((i + 1) / len(article_urls))
            time.sleep(0.3)  # 서버 부담 감소
        
        progress_bar.empty()
        
        return articles

# 검색 함수
def search_articles(query, articles):
    """수집된 기사에서 관련 기사를 검색합니다."""
    if not articles:
        return []
    
    query_lower = query.lower()
    results = []
    
    for article in articles:
        score = 0
        title_lower = article["title"].lower()
        content_lower = article["content"].lower()
        
        # 쿼리 키워드 매칭
        keywords = query_lower.split()
        for keyword in keywords:
            if keyword in title_lower:
                score += 5
            if keyword in content_lower:
                score += 2
            if keyword in article["region"].lower():
                score += 3
        
        if score > 0:
            results.append((score, article))
    
    # 점수 순으로 정렬
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:5]]  # 상위 5개만 반환

# OpenAI 응답 생성
def get_gpt_response(query, search_results):
    if not api_key:
        return "OpenAI API 키가 설정되지 않았습니다."
    
    if not search_results:
        return "관련 기사를 찾을 수 없습니다."

    try:
        client = OpenAI(api_key=api_key.strip())
        
        # 컨텍스트 구성
        context = "다음은 중앙일보의 최신 부동산 뉴스입니다:\n\n"
        
        for i, article in enumerate(search_results):
            context += f"[기사 {i+1}]\n"
            context += f"제목: {article['title']}\n"
            context += f"날짜: {article['date']}\n"
            context += f"지역: {article['region']}\n"
            context += f"가격동향: {article['price_trend']}\n"
            context += f"내용: {article['content'][:500]}...\n"
            context += f"출처: {article['url']}\n\n"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 부동산 전문가입니다. 최신 뉴스를 바탕으로 정확하고 구체적으로 답변하세요."},
                {"role": "user", "content": f"{context}\n질문: {query}"}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"응답 생성 중 오류: {str(e)}"

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "articles" not in st.session_state:
    st.session_state.articles = []
if "last_crawl" not in st.session_state:
    st.session_state.last_crawl = None

# 사이드바 - 데이터 수집
st.sidebar.header("📰 뉴스 수집")

# 검색 키워드 설정
search_keywords = st.sidebar.text_input(
    "검색 키워드", 
    value="부동산 가격",
    help="중앙일보에서 검색할 키워드를 입력하세요"
)

# 페이지 수 설정
num_pages = st.sidebar.slider("검색 페이지 수", 1, 5, 2)

# 데이터 수집 버튼
if st.sidebar.button("🔄 최신 뉴스 수집", type="primary"):
    articles = collect_real_estate_news(search_keywords, num_pages)
    if articles:
        st.session_state.articles = articles
        st.session_state.last_crawl = datetime.now()
        st.success(f"✅ {len(articles)}개의 기사를 수집했습니다!")
    else:
        st.warning("수집된 기사가 없습니다.")

# 수집된 데이터 정보
if st.session_state.articles:
    st.sidebar.success(f"📊 수집된 기사: {len(st.session_state.articles)}개")
    if st.session_state.last_crawl:
        st.sidebar.info(f"마지막 수집: {st.session_state.last_crawl.strftime('%Y-%m-%d %H:%M')}")
else:
    st.sidebar.info("아직 뉴스를 수집하지 않았습니다.\n'최신 뉴스 수집' 버튼을 클릭하세요.")

# 수집된 기사 미리보기
if st.sidebar.checkbox("수집된 기사 보기") and st.session_state.articles:
    with st.sidebar.expander("최근 기사 목록"):
        for article in st.session_state.articles[:5]:
            st.write(f"**{article['title'][:30]}...**")
            st.write(f"📅 {article['date']} | 📍 {article['region']} | 📈 {article['price_trend']}")
            st.write("---")

# 대화 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 사용자 입력
if prompt := st.chat_input("질문을 입력하세요 (예: 강남 아파트 가격은 어떻게 되고 있나요?)"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # 응답 생성
    with st.chat_message("assistant"):
        if not st.session_state.articles:
            response = "먼저 사이드바에서 '최신 뉴스 수집' 버튼을 클릭하여 최신 뉴스를 수집해주세요."
            st.write(response)
        else:
            with st.spinner("답변 생성 중..."):
                # 관련 기사 검색
                relevant_articles = search_articles(prompt, st.session_state.articles)
                
                if api_key:
                    response = get_gpt_response(prompt, relevant_articles)
                else:
                    # API 키 없이 간단한 응답
                    response = f"관련 기사 {len(relevant_articles)}개를 찾았습니다:\n\n"
                    for i, article in enumerate(relevant_articles[:3]):
                        response += f"**{i+1}. {article['title']}**\n"
                        response += f"- 날짜: {article['date']}\n"
                        response += f"- 지역: {article['region']}\n"
                        response += f"- 동향: {article['price_trend']}\n"
                        response += f"- 내용: {article['content'][:200]}...\n\n"
                
                st.write(response)
                
                # 출처 표시
                if relevant_articles:
                    with st.expander("📎 참고 기사"):
                        for article in relevant_articles[:3]:
                            st.write(f"- [{article['title']}]({article['url']})")
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# 예시 질문
st.sidebar.header("💡 예시 질문")
examples = [
    "강남 아파트 가격 동향은?",
    "최근 전세 시장은 어떤가요?",
    "서울 부동산 가격이 오르고 있나요?",
    "송파구 아파트 시세는?"
]

for example in examples:
    if st.sidebar.button(example, key=f"ex_{example}"):
        st.rerun()

# 대화 초기화
if st.sidebar.button("🗑️ 대화 초기화"):
    st.session_state.messages = []
    st.rerun()
