# Enhanced AI News Analysis Agent with Modern UI
import streamlit as st
import json
from openai import OpenAI
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import time
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# 페이지 설정
st.set_page_config(
    page_title="AI News Intelligence Hub", 
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS with modern animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Dark theme variables */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --warning-gradient: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        --dark-bg: #0f0f0f;
        --card-bg: #1a1a1a;
        --text-primary: #ffffff;
        --text-secondary: #a0a0a0;
    }
    
    /* Main container */
    .main {
        padding-top: 2rem;
        background-color: var(--dark-bg);
    }
    
    /* Animated gradient header */
    .main-header {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
        padding: 3rem;
        border-radius: 30px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: rotate 20s linear infinite;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    /* Modern card design */
    .news-card {
        background: var(--card-bg);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        margin-bottom: 1.5rem;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 1px solid rgba(255,255,255,0.05);
        position: relative;
        overflow: hidden;
    }
    
    .news-card::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(45deg, #667eea, #764ba2, #f093fb, #f5576c);
        border-radius: 20px;
        opacity: 0;
        z-index: -1;
        transition: opacity 0.3s ease;
    }
    
    .news-card:hover::before {
        opacity: 1;
    }
    
    .news-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 50px rgba(102, 126, 234, 0.3);
    }
    
    /* Glassmorphism effect */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    /* Metric cards with animations */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9), rgba(118, 75, 162, 0.9));
        color: white;
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(0.8); opacity: 0.5; }
        50% { transform: scale(1.2); opacity: 0.8; }
    }
    
    /* Modern buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 1rem 2rem;
        border-radius: 50px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
        position: relative;
        overflow: hidden;
        z-index: 1;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s ease;
        z-index: -1;
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.5);
    }
    
    /* Chat messages with modern design */
    .stChatMessage {
        background: var(--card-bg);
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Animated loading */
    .loading-wave {
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    .loading-wave span {
        width: 5px;
        height: 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 5px;
        animation: wave 1.2s ease-in-out infinite;
    }
    
    .loading-wave span:nth-child(1) { animation-delay: 0s; }
    .loading-wave span:nth-child(2) { animation-delay: 0.1s; }
    .loading-wave span:nth-child(3) { animation-delay: 0.2s; }
    .loading-wave span:nth-child(4) { animation-delay: 0.3s; }
    .loading-wave span:nth-child(5) { animation-delay: 0.4s; }
    
    @keyframes wave {
        0%, 100% { transform: scaleY(0.5); }
        50% { transform: scaleY(1); }
    }
    
    /* Neon glow effect */
    .neon-text {
        color: #fff;
        text-shadow: 
            0 0 10px #667eea,
            0 0 20px #667eea,
            0 0 30px #667eea,
            0 0 40px #764ba2;
        animation: neon-flicker 1.5s infinite alternate;
    }
    
    @keyframes neon-flicker {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    /* Floating elements */
    .floating {
        animation: float 6s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--dark-bg);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Tag pills */
    .tag-pill {
        display: inline-block;
        padding: 0.5rem 1rem;
        margin: 0.25rem;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
        border: 1px solid rgba(102, 126, 234, 0.5);
        border-radius: 50px;
        font-size: 0.875rem;
        color: #fff;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .tag-pill:hover {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.4), rgba(118, 75, 162, 0.4));
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# API 키 관리 클래스
class APIManager:
    @staticmethod
    def get_api_keys():
        """API 키를 안전하게 가져옵니다."""
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

# 뉴스 분석 클래스
class NewsAnalyzer:
    def __init__(self, naver_client_id, naver_client_secret):
        self.naver_client_id = naver_client_id
        self.naver_client_secret = naver_client_secret
    
    @st.cache_data(ttl=1800)
    def search_news(_self, query, display=20, start=1, sort="date"):
        """네이버 뉴스 검색 API를 사용하여 뉴스를 검색합니다."""
        if not _self.naver_client_id or not _self.naver_client_secret:
            st.error("⚠️ 네이버 API 키가 설정되지 않았습니다!")
            return []
        
        try:
            encText = urllib.parse.quote(query)
            url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display}&start={start}&sort={sort}"
            
            request = urllib.request.Request(url)
            request.add_header("X-Naver-Client-Id", _self.naver_client_id)
            request.add_header("X-Naver-Client-Secret", _self.naver_client_secret)
            
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
                    
                    # 카테고리 자동 분류
                    category = _self._categorize_article(title, description)
                    
                    # 감정 분석 (간단한 버전)
                    sentiment = _self._analyze_sentiment(title + " " + description)
                    
                    articles.append({
                        "title": title,
                        "content": description,
                        "date": pub_date.strftime("%Y-%m-%d"),
                        "time": pub_date.strftime("%H:%M"),
                        "category": category,
                        "sentiment": sentiment,
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
    
    def _categorize_article(self, title, content):
        """기사 카테고리 자동 분류"""
        text = (title + " " + content).lower()
        
        categories = {
            "💹 경제": ["경제", "금리", "환율", "주식", "부동산", "물가", "실업", "투자", "증시", "코스피"],
            "🏛️ 정치": ["정치", "국회", "대통령", "선거", "정당", "외교", "정책", "장관", "의원", "정부"],
            "💻 IT/과학": ["AI", "인공지능", "반도체", "전기차", "바이오", "우주", "메타버스", "IT", "기술", "스타트업"],
            "🎭 문화": ["문화", "K팝", "드라마", "영화", "스포츠", "게임", "관광", "예술", "공연", "전시"],
            "👥 사회": ["사회", "교육", "의료", "복지", "범죄", "환경", "노동", "사고", "재난", "날씨"],
            "🌍 국제": ["국제", "미국", "중국", "일본", "러시아", "유럽", "중동", "UN", "글로벌", "해외"]
        }
        
        scores = {}
        for cat, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[cat] = score
        
        return max(scores, key=scores.get) if scores else "📰 일반"
    
    def _analyze_sentiment(self, text):
        """간단한 감정 분석"""
        positive_words = ["성장", "상승", "증가", "호전", "개선", "긍정", "성공", "달성", "혁신", "발전"]
        negative_words = ["하락", "감소", "위기", "우려", "부정", "실패", "위험", "악화", "침체", "논란"]
        
        text_lower = text.lower()
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        
        if positive_score > negative_score:
            return "😊 긍정적"
        elif negative_score > positive_score:
            return "😟 부정적"
        else:
            return "😐 중립적"

# GPT 분석 클래스
class GPTAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
    
    def analyze_news(self, query, articles):
        """GPT를 사용하여 뉴스 분석"""
        if not self.api_key:
            return self._simple_analysis(query, articles)
        
        try:
            client = OpenAI(api_key=self.api_key.strip())
            
            context = self._build_context(articles)
            
            system_prompt = """당신은 최고의 뉴스 분석 전문가입니다. 
            
주어진 뉴스 기사들을 깊이 있게 분석하여:
1. 핵심 내용을 명확하게 요약
2. 트렌드와 패턴 파악
3. 미래 전망 제시
4. 실행 가능한 인사이트 도출

답변 형식:
📊 **핵심 요약**
- 주요 포인트들

🔍 **상세 분석**
- 깊이 있는 분석 내용

📈 **트렌드 & 전망**
- 현재 트렌드와 미래 예측

💡 **실행 가능한 인사이트**
- 구체적인 제안사항

적절한 이모지와 포맷팅을 사용하여 읽기 쉽게 작성하세요."""
            
            user_prompt = f"{context}\n\n사용자 질문: {query}\n\n위 기사들을 종합적으로 분석하여 전문가 수준의 인사이트를 제공해주세요."
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return self._simple_analysis(query, articles)
    
    def _build_context(self, articles):
        """컨텍스트 구성"""
        context = "분석할 뉴스 기사들:\n\n"
        for i, article in enumerate(articles[:5]):
            context += f"[기사 {i+1}]\n"
            context += f"제목: {article['title']}\n"
            context += f"날짜: {article['date']} {article.get('time', '')}\n"
            context += f"카테고리: {article.get('category', '일반')}\n"
            context += f"감정: {article.get('sentiment', '중립')}\n"
            context += f"내용: {article['content']}\n"
            context += f"출처: {article['source']}\n\n"
        return context
    
    def _simple_analysis(self, query, articles):
        """GPT 없이 간단한 분석 제공"""
        if not articles:
            return "관련 뉴스를 찾을 수 없습니다. 😔"
        
        response = f"📰 **'{query}'에 대한 분석 결과:**\n\n"
        
        # 카테고리별 분류
        categories = {}
        for article in articles:
            cat = article.get('category', '일반')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(article)
        
        response += "📊 **카테고리별 분포:**\n"
        for cat, arts in categories.items():
            response += f"- {cat}: {len(arts)}건\n"
        
        response += "\n🔍 **주요 기사:**\n\n"
        for i, article in enumerate(articles[:3]):
            response += f"### {i+1}. {article['title']}\n"
            response += f"📅 {article['date']} | 🏷️ {article.get('category', '일반')} | {article.get('sentiment', '😐 중립')}\n\n"
            response += f"{article['content'][:200]}...\n\n"
            response += f"🔗 [기사 전문 보기]({article['url']})\n\n"
            response += "---\n\n"
        
        return response

# 데이터 시각화 클래스
class DataVisualizer:
    @staticmethod
    def create_category_chart(articles):
        """카테고리별 분포 차트"""
        if not articles:
            return None
        
        categories = [art.get('category', '일반') for art in articles]
        cat_counts = Counter(categories)
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(cat_counts.keys()),
                y=list(cat_counts.values()),
                marker=dict(
                    color=list(range(len(cat_counts))),
                    colorscale='Viridis',
                    showscale=False
                ),
                text=list(cat_counts.values()),
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="📊 카테고리별 뉴스 분포",
            xaxis_title="카테고리",
            yaxis_title="기사 수",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_sentiment_chart(articles):
        """감정 분석 차트"""
        if not articles:
            return None
        
        sentiments = [art.get('sentiment', '😐 중립적') for art in articles]
        sent_counts = Counter(sentiments)
        
        fig = go.Figure(data=[go.Pie(
            labels=list(sent_counts.keys()),
            values=list(sent_counts.values()),
            hole=.3,
            marker=dict(
                colors=['#4CAF50', '#FFC107', '#F44336']
            )
        )])
        
        fig.update_layout(
            title="😊 감정 분석 결과",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_timeline_chart(articles):
        """시간대별 기사 분포"""
        if not articles:
            return None
        
        # 날짜별 그룹화
        date_counts = Counter([art['date'] for art in articles])
        dates = sorted(date_counts.keys())
        counts = [date_counts[date] for date in dates]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=counts,
            mode='lines+markers',
            name='기사 수',
            line=dict(color='#667eea', width=3),
            marker=dict(size=10, color='#764ba2')
        ))
        
        fig.update_layout(
            title="📅 시간대별 기사 분포",
            xaxis_title="날짜",
            yaxis_title="기사 수",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400
        )
        
        return fig

# 메인 앱 클래스
class NewsIntelligenceApp:
    def __init__(self):
        self.setup_session_state()
        self.api_manager = APIManager()
        openai_key, naver_id, naver_secret = self.api_manager.get_api_keys()
        self.news_analyzer = NewsAnalyzer(naver_id, naver_secret)
        self.gpt_analyzer = GPTAnalyzer(openai_key)
        self.visualizer = DataVisualizer()
    
    def setup_session_state(self):
        """세션 상태 초기화"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "articles" not in st.session_state:
            st.session_state.articles = []
        if "search_keyword" not in st.session_state:
            st.session_state.search_keyword = ""
        if "analysis_mode" not in st.session_state:
            st.session_state.analysis_mode = "chat"
    
    def render_header(self):
        """헤더 렌더링"""
        st.markdown("""
        <div class="main-header">
            <h1 class="neon-text" style="margin: 0; font-size: 3rem; position: relative; z-index: 1;">
                🚀 AI News Intelligence Hub
            </h1>
            <p style="margin: 1rem 0 0 0; font-size: 1.3rem; opacity: 0.9; position: relative; z-index: 1;">
                실시간 뉴스 수집 • AI 기반 심층 분석 • 데이터 시각화
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """사이드바 렌더링"""
        st.sidebar.markdown("## ⚙️ Control Center")
        
        # API 상태 표시
        self._show_api_status()
        
        # 분석 모드 선택
        st.sidebar.markdown("### 🎯 분석 모드")
        mode = st.sidebar.radio(
            "모드 선택",
            ["💬 대화형 분석", "📊 데이터 시각화", "🔍 심층 분석"],
            label_visibility="collapsed"
        )
        
        if mode == "💬 대화형 분석":
            st.session_state.analysis_mode = "chat"
        elif mode == "📊 데이터 시각화":
            st.session_state.analysis_mode = "visualization"
        else:
            st.session_state.analysis_mode = "deep"
        
        # 뉴스 검색
        st.sidebar.markdown("### 🔍 뉴스 수집")
        self._render_search_section()
        
        # 트렌딩 토픽
        self._render_trending_topics()
    
    def _show_api_status(self):
        """API 상태 표시"""
        openai_key, naver_id, naver_secret = self.api_manager.get_api_keys()
        
        api_status = []
        if openai_key and openai_key.startswith("sk-"):
            api_status.append("✅ OpenAI")
        else:
            api_status.append("❌ OpenAI")
        
        if naver_id and naver_secret:
            api_status.append("✅ Naver")
        else:
            api_status.append("❌ Naver")
        
        st.sidebar.markdown(f"""
        <div class="glass-card" style="margin-bottom: 1rem;">
            <h4 style="margin: 0; color: #fff;">🔌 API 연결 상태</h4>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; color: #fff;">
                {" | ".join(api_status)}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_search_section(self):
        """검색 섹션 렌더링"""
        search_keyword = st.sidebar.text_input(
            "검색어 입력", 
            placeholder="예: AI, 경제, 선거...",
            help="검색하고 싶은 뉴스 주제를 입력하세요"
        )
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            num_articles = st.selectbox("📊 기사 수", [20, 30, 50, 100], index=0)
        with col2:
            sort_option = st.selectbox("🔄 정렬", ["date", "sim"], 
                                     format_func=lambda x: "최신순" if x == "date" else "정확도순")
        
        if st.sidebar.button("🚀 뉴스 수집", type="primary", use_container_width=True):
            if search_keyword:
                self._collect_news(search_keyword, num_articles, sort_option)
            else:
                st.error("검색어를 입력해주세요!")
        
        if st.sidebar.button("🗑️ 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.articles = []
            st.rerun()
    
    def _collect_news(self, keyword, num_articles, sort_option):
        """뉴스 수집"""
        with st.spinner("뉴스를 수집하고 있습니다..."):
            articles = self.news_analyzer.search_news(keyword, display=num_articles, sort=sort_option)
            if articles:
                st.session_state.articles = articles
                st.session_state.search_keyword = keyword
                st.success(f"✅ {len(articles)}개 기사 수집 완료!")
                
                # 자동 요약 생성
                if st.session_state.analysis_mode == "deep":
                    summary = self._generate_auto_summary(articles)
                    st.session_state.messages.append({"role": "assistant", "content": summary})
                
                st.balloons()
            else:
                st.warning("검색 결과가 없습니다.")
    
    def _generate_auto_summary(self, articles):
        """자동 요약 생성"""
        return self.gpt_analyzer.analyze_news(
            f"{st.session_state.search_keyword}에 대한 종합 분석", 
            articles[:10]
        )
    
    def _render_trending_topics(self):
        """트렌딩 토픽 렌더링"""
        st.sidebar.markdown("### 🔥 실시간 트렌드")
        
        trending = {
            "🔥 HOT": ["삼성전자", "테슬라", "ChatGPT", "부동산", "금리"],
            "📈 급상승": ["메타버스", "양자컴퓨터", "K-뷰티", "전기차", "ESG"],
            "🌐 글로벌": ["우크라이나", "인플레이션", "기후변화", "암호화폐", "AI규제"]
        }
        
        for category, keywords in trending.items():
            st.sidebar.markdown(f"**{category}**")
            cols = st.sidebar.columns(2)
            for i, keyword in enumerate(keywords):
                with cols[i % 2]:
                    if st.button(f"{keyword}", key=f"trend_{category}_{keyword}", 
                               use_container_width=True):
                        self._collect_news(keyword, 20, "date")
    
    def render_main_content(self):
        """메인 컨텐츠 렌더링"""
        if not st.session_state.articles:
            self._render_welcome_screen()
        else:
            if st.session_state.analysis_mode == "chat":
                self._render_chat_mode()
            elif st.session_state.analysis_mode == "visualization":
                self._render_visualization_mode()
            else:
                self._render_deep_analysis_mode()
    
    def _render_welcome_screen(self):
        """환영 화면"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="glass-card floating" style="text-align: center; padding: 4rem;">
                <h2 class="neon-text" style="font-size: 2.5rem;">
                    🎯 뉴스 인텔리전스 시작하기
                </h2>
                <p style="font-size: 1.2rem; color: #a0a0a0; margin: 2rem 0;">
                    AI가 실시간 뉴스를 분석하여 인사이트를 제공합니다
                </p>
                
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin-top: 3rem;">
                    <div class="glass-card">
                        <h3 style="color: #667eea;">🔍</h3>
                        <h4>스마트 검색</h4>
                        <p style="font-size: 0.9rem; color: #a0a0a0;">
                            키워드 기반 정밀 검색
                        </p>
                    </div>
                    <div class="glass-card">
                        <h3 style="color: #764ba2;">🤖</h3>
                        <h4>AI 분석</h4>
                        <p style="font-size: 0.9rem; color: #a0a0a0;">
                            GPT-4 기반 심층 분석
                        </p>
                    </div>
                    <div class="glass-card">
                        <h3 style="color: #f093fb;">📊</h3>
                        <h4>시각화</h4>
                        <p style="font-size: 0.9rem; color: #a0a0a0;">
                            인터랙티브 데이터 차트
                        </p>
                    </div>
                </div>
                
                <div class="loading-wave" style="justify-content: center; margin-top: 3rem;">
                    <span></span>
                    <span></span>
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_chat_mode(self):
        """대화형 모드"""
        # 통계 표시
        self._show_statistics()
        
        # 대화 내용 표시
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # 사용자 입력
        if prompt := st.chat_input("뉴스에 대해 질문하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("AI가 분석 중입니다..."):
                    response = self.gpt_analyzer.analyze_news(prompt, st.session_state.articles)
                st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    def _render_visualization_mode(self):
        """시각화 모드"""
        st.markdown("## 📊 데이터 시각화 대시보드")
        
        if st.session_state.articles:
            col1, col2 = st.columns(2)
            
            with col1:
                # 카테고리 차트
                cat_fig = self.visualizer.create_category_chart(st.session_state.articles)
                if cat_fig:
                    st.plotly_chart(cat_fig, use_container_width=True)
            
            with col2:
                # 감정 분석 차트
                sent_fig = self.visualizer.create_sentiment_chart(st.session_state.articles)
                if sent_fig:
                    st.plotly_chart(sent_fig, use_container_width=True)
            
            # 타임라인 차트
            timeline_fig = self.visualizer.create_timeline_chart(st.session_state.articles)
            if timeline_fig:
                st.plotly_chart(timeline_fig, use_container_width=True)
            
            # 워드 클라우드 (텍스트 기반)
            self._render_word_cloud()
    
    def _render_deep_analysis_mode(self):
        """심층 분석 모드"""
        st.markdown("## 🔍 AI 심층 분석 리포트")
        
        if st.session_state.messages:
            for msg in st.session_state.messages:
                if msg["role"] == "assistant":
                    st.markdown(msg["content"])
        
        # 추가 분석 옵션
        with st.expander("🎯 추가 분석 옵션"):
            analysis_type = st.selectbox(
                "분석 유형 선택",
                ["종합 분석", "트렌드 분석", "감정 분석", "예측 분석"]
            )
            
            if st.button("🚀 분석 실행"):
                with st.spinner("심층 분석을 진행하고 있습니다..."):
                    analysis = self.gpt_analyzer.analyze_news(
                        f"{analysis_type}: {st.session_state.search_keyword}",
                        st.session_state.articles
                    )
                    st.markdown(analysis)
                    st.session_state.messages.append({"role": "assistant", "content": analysis})
    
    def _show_statistics(self):
        """통계 정보 표시"""
        if st.session_state.articles:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h4 style="margin: 0; opacity: 0.8;">🔍 검색어</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 2rem; font-weight: bold;">
                        {st.session_state.search_keyword}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card" style="background: var(--secondary-gradient);">
                    <h4 style="margin: 0; opacity: 0.8;">📰 기사 수</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 2rem; font-weight: bold;">
                        {len(st.session_state.articles)}개
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                latest_date = max(art['date'] for art in st.session_state.articles)
                st.markdown(f"""
                <div class="metric-card" style="background: var(--success-gradient);">
                    <h4 style="margin: 0; opacity: 0.8;">📅 최신 기사</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1.5rem; font-weight: bold;">
                        {latest_date}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                categories = [art.get('category', '일반') for art in st.session_state.articles]
                most_common = max(set(categories), key=categories.count)
                st.markdown(f"""
                <div class="metric-card" style="background: var(--warning-gradient);">
                    <h4 style="margin: 0; opacity: 0.8;">🏷️ 주요 카테고리</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; font-weight: bold;">
                        {most_common}
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    def _render_word_cloud(self):
        """워드 클라우드 렌더링"""
        st.markdown("### ☁️ 주요 키워드")
        
        # 간단한 키워드 추출
        all_text = " ".join([art['title'] + " " + art['content'] for art in st.session_state.articles])
        words = all_text.split()
        
        # 불용어 제거
        stopwords = ['의', '가', '이', '은', '들', '는', '좀', '잘', '과', '를', '으로', '자', '에', '한', '하다']
        words = [w for w in words if len(w) > 1 and w not in stopwords]
        
        # 빈도수 계산
        word_freq = Counter(words)
        top_words = word_freq.most_common(20)
        
        # 태그 클라우드 스타일로 표시
        tags_html = ""
        for word, freq in top_words:
            size = min(2.5, 0.8 + (freq / top_words[0][1]) * 1.7)
            tags_html += f'<span class="tag-pill" style="font-size: {size}rem;">{word}</span>'
        
        st.markdown(f'<div style="text-align: center; padding: 2rem;">{tags_html}</div>', 
                   unsafe_allow_html=True)
    
    def run(self):
        """앱 실행"""
        self.render_header()
        self.render_sidebar()
        self.render_main_content()

# 앱 실행
if __name__ == "__main__":
    app = NewsIntelligenceApp()
    app.run()
