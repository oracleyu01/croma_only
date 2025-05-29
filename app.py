# 대화형 쳇봇 애플리케이션에 필요한 라이브러리 임포트
import streamlit as st
import json
from openai import OpenAI
import re

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
    with st.sidebar.expander("API 키 설정 방법"):
        st.write("""
        **Streamlit Cloud:**
        1. App settings → Secrets 클릭
        2. 다음 내용 추가:
        ```
        OPENAI_API_KEY = "sk-..."
        ```
        
        **로컬 환경:**
        1. `.streamlit/secrets.toml` 파일 생성
        2. 위와 같은 내용 추가
        """)

# 페이지 제목
st.title("🏠 부동산 가격 분석 AI 데이터 분석가")
st.write("뉴스 기사 및 보고서에서 수집한 부동산 가격 데이터에 대해 질문해보세요.")

# 이미지 표시 (옵션)
try:
    st.image("realestate.png", use_container_width=True)
except:
    pass

# 샘플 데이터 정의
SAMPLE_DATA = [
    {
        "content": "서울 강남구 아파트 평균 매매가격이 전월 대비 2.3% 상승했습니다. 특히 대치동과 삼성동 일대의 대단지 아파트를 중심으로 가격 상승세가 뚜렷하게 나타났습니다. 전문가들은 이러한 상승세가 당분간 지속될 것으로 전망하고 있습니다.",
        "title": "강남구 부동산 시장 동향",
        "metadata": {"region": "강남구", "date": "2025-01", "price_trend": "상승", "article_type": "시장분석"}
    },
    {
        "content": "송파구 잠실 일대 전세 가격이 안정세를 보이고 있습니다. 신규 아파트 공급과 함께 전세 수요가 분산되면서 가격 상승폭이 둔화되었습니다. 잠실 롯데월드타워 인근 아파트의 경우 전세가율이 60% 수준을 유지하고 있습니다.",
        "title": "송파구 전세 시장 분석",
        "metadata": {"region": "송파구", "date": "2025-01", "price_trend": "안정", "article_type": "시장분석"}
    },
    {
        "content": "정부의 부동산 규제 완화 정책 발표 이후 서울 주요 지역의 거래량이 증가하고 있습니다. 특히 강남 3구를 중심으로 매수 문의가 늘어나고 있습니다. 대출 규제 완화와 양도세 부담 경감이 주요 요인으로 분석됩니다.",
        "title": "부동산 정책 영향 분석",
        "metadata": {"region": "서울", "date": "2025-01", "price_trend": "거래증가", "article_type": "정책분석"}
    },
    {
        "content": "마포구 공덕동 일대 신축 오피스텔 분양가가 평당 3,000만원을 돌파했습니다. 교통 호재와 개발 기대감으로 투자 수요가 몰리고 있습니다. 공덕역 트리플역세권의 입지적 장점이 가격 상승을 견인하고 있습니다.",
        "title": "마포구 오피스텔 시장",
        "metadata": {"region": "마포구", "date": "2025-01", "price_trend": "상승", "article_type": "분양정보"}
    },
    {
        "content": "경기도 성남시 분당구 주택 시장이 활기를 띠고 있습니다. GTX 개통 기대감과 함께 전세가율이 하락하면서 매매 전환 수요가 증가하고 있습니다. 판교 테크노밸리 인근 아파트를 중심으로 거래가 활발합니다.",
        "title": "분당 부동산 시장 동향",
        "metadata": {"region": "분당구", "date": "2025-01", "price_trend": "활성화", "article_type": "시장분석"}
    }
]

# 간단한 검색 함수
def search_data(query, data=SAMPLE_DATA):
    """키워드 기반 검색"""
    query_lower = query.lower()
    results = []
    
    # 각 문서에 대해 점수 계산
    for item in data:
        score = 0
        content_lower = item["content"].lower()
        title_lower = item["title"].lower()
        
        # 쿼리를 단어로 분리
        keywords = query_lower.split()
        
        for keyword in keywords:
            # 제목에 포함되면 높은 점수
            if keyword in title_lower:
                score += 3
            # 내용에 포함되면 중간 점수
            if keyword in content_lower:
                score += 2
            # 메타데이터에 포함되면 낮은 점수
            metadata_str = str(item["metadata"]).lower()
            if keyword in metadata_str:
                score += 1
            
            # 지역명 특별 처리
            if "region" in item["metadata"] and keyword in item["metadata"]["region"].lower():
                score += 5
        
        if score > 0:
            results.append((score, item))
    
    # 점수 순으로 정렬
    results.sort(key=lambda x: x[0], reverse=True)
    
    # 상위 3개만 반환
    return [r[1] for r in results[:3]] if results else SAMPLE_DATA[:3]

# OpenAI를 활용한 응답 생성
def get_gpt_response(query, search_results, api_key):
    if not api_key:
        return "OpenAI API 키가 설정되지 않았습니다."

    try:
        client = OpenAI(api_key=api_key.strip())
        
        # 컨텍스트 구성
        context = "다음은 부동산 가격 관련 데이터입니다:\n\n"
        
        for i, result in enumerate(search_results):
            context += f"[문서 {i+1}]\n"
            context += f"제목: {result.get('title', '제목 없음')}\n"
            
            if result.get('metadata'):
                metadata = result['metadata']
                context += f"지역: {metadata.get('region', 'N/A')}\n"
                context += f"날짜: {metadata.get('date', 'N/A')}\n"
                context += f"가격동향: {metadata.get('price_trend', 'N/A')}\n"
                context += f"유형: {metadata.get('article_type', 'N/A')}\n"
            
            context += f"내용: {result['content']}\n\n"
        
        # 시스템 프롬프트
        system_prompt = """당신은 부동산 시장 및 가격 분석 전문가입니다. 
        제공된 문서들을 바탕으로 사용자 질문에 정확하고 구체적으로 답변해주세요.
        숫자나 통계가 있다면 반드시 포함시키고, 지역별 특성을 고려하여 설명하세요."""
        
        # API 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n질문: {query}"}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        if "api key" in error_msg.lower():
            return "OpenAI API 키 인증에 실패했습니다. API 키를 확인해주세요."
        else:
            return f"응답 생성 중 오류가 발생했습니다: {error_msg}"

# 간단한 응답 생성
def get_simple_response(query, search_results):
    if not search_results:
        return "관련 데이터를 찾을 수 없습니다."
    
    result_text = f"💡 '{query}'에 대한 검색 결과입니다:\n\n"
    
    for i, result in enumerate(search_results):
        result_text += f"### {i+1}. {result.get('title', f'문서 {i+1}')}\n"
        
        # 메타데이터 표시
        if result.get('metadata'):
            meta = result['metadata']
            result_text += f"📍 지역: {meta.get('region', 'N/A')} | "
            result_text += f"📅 시기: {meta.get('date', 'N/A')} | "
            result_text += f"📊 동향: {meta.get('price_trend', 'N/A')}\n\n"
        
        # 내용 요약
        content = result['content']
        if len(content) > 200:
            content = content[:200] + "..."
        result_text += f"{content}\n\n"
        result_text += "---\n\n"
    
    result_text += "\n💡 더 자세한 분석을 원하시면 OpenAI API 키를 설정해주세요."
    return result_text

# 챗봇 응답 생성
def chat_response(question):
    # 데이터 검색
    search_results = search_data(question)
    
    # API 키가 있으면 GPT 사용, 없으면 간단한 응답
    if api_key and api_key.startswith("sk-"):
        return get_gpt_response(question, search_results, api_key)
    else:
        return get_simple_response(question, search_results)

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 이전 대화 내용 표시
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 받기
if prompt := st.chat_input("질문을 입력하세요 (예: 서울 강남 아파트 가격 동향은 어떻게 되나요?)"):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 대화 이력에 저장
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # 응답 생성
    with st.spinner("답변을 준비하고 있습니다..."):
        response = chat_response(prompt)
    
    # 응답 표시
    with st.chat_message("assistant"):
        st.markdown(response)
    
    # 대화 이력에 저장
    st.session_state.chat_history.append({"role": "assistant", "content": response})

# 사이드바 예시 질문
st.sidebar.header("예시 질문")
example_questions = [
    "서울 강남 아파트 가격 동향은 어떻게 되나요?",
    "최근 전세 시장의 변화 추이를 알려주세요.",
    "어떤 정책이 부동산 가격에 영향을 미쳤나요?",
    "송파구와 강남구의 아파트 가격을 비교해주세요.",
    "마포구 오피스텔 투자 전망은?",
    "분당 부동산 시장은 어떤가요?"
]

# 예시 질문 버튼
for i, question in enumerate(example_questions):
    if st.sidebar.button(question, key=f"ex_{i}"):
        # 대화에 추가
        st.session_state.chat_history.append({"role": "user", "content": question})
        response = chat_response(question)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

# 데이터 시각화
st.sidebar.header("데이터 시각화")
if st.sidebar.button("가격 동향 차트 보기"):
    st.session_state.show_chart = True

if "show_chart" in st.session_state and st.session_state.show_chart:
    st.subheader("📊 주요 지역 부동산 가격 동향")
    
    # 샘플 차트 데이터
    chart_data = {
        "강남": [100, 105, 110, 108, 115, 120],
        "송파": [90, 95, 100, 103, 107, 110],
        "마포": [80, 82, 85, 87, 90, 92],
        "분당": [85, 87, 90, 92, 95, 98]
    }
    
    st.line_chart(chart_data)
    st.caption("최근 6개월 부동산 가격 지수 (기준점: 100)")
    
    # 차트 닫기 버튼
    if st.button("차트 닫기"):
        st.session_state.show_chart = False
        st.rerun()

# 대화 기록 초기화
if st.sidebar.button("대화 기록 초기화"):
    st.session_state.chat_history = []
    st.rerun()

# 하단 정보
st.sidebar.markdown("---")
st.sidebar.info("""
**데이터 소스**: 샘플 데이터 (데모용)
**검색 방식**: 키워드 매칭
**AI 모델**: GPT-4o-mini (API 키 필요)
""")
