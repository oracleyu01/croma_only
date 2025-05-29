# 대화형 쳇봇 애플리케이션에 필요한 라이브러리 임포트
import streamlit as st
import json
from openai import OpenAI
import re

# ChromaDB import 시도
USE_CHROMADB = True
try:
    import chromadb
    from chromadb.utils import embedding_functions
except Exception as e:
    USE_CHROMADB = False
    st.warning(f"ChromaDB를 로드할 수 없어 간단한 모드로 실행됩니다: {e}")

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

# 컬렉션 이름 입력 (사이드바)
collection_name = st.sidebar.text_input("사용할 컬렉션 이름", value="real_estate_prices_20250511")

# 페이지 제목
st.title("🏠 부동산 가격 분석 AI 데이터 분석가")
st.write("뉴스 기사 및 보고서에서 수집한 부동산 가격 데이터에 대해 질문해보세요.")

# 기본 샘플 데이터 (ChromaDB 없이도 작동)
SAMPLE_DATA = [
    {
        "content": "서울 강남구 아파트 평균 매매가격이 전월 대비 2.3% 상승했습니다. 특히 대치동과 삼성동 일대의 대단지 아파트를 중심으로 가격 상승세가 뚜렷하게 나타났습니다.",
        "title": "강남구 부동산 시장 동향",
        "metadata": {"region": "강남구", "date": "2025-01", "price_trend": "상승", "article_type": "시장분석"}
    },
    {
        "content": "송파구 잠실 일대 전세 가격이 안정세를 보이고 있습니다. 신규 아파트 공급과 함께 전세 수요가 분산되면서 가격 상승폭이 둔화되었습니다.",
        "title": "송파구 전세 시장 분석",
        "metadata": {"region": "송파구", "date": "2025-01", "price_trend": "안정", "article_type": "시장분석"}
    },
    {
        "content": "정부의 부동산 규제 완화 정책 발표 이후 서울 주요 지역의 거래량이 증가하고 있습니다. 특히 강남 3구를 중심으로 매수 문의가 늘어나고 있습니다.",
        "title": "부동산 정책 영향 분석",
        "metadata": {"region": "서울", "date": "2025-01", "price_trend": "거래증가", "article_type": "정책분석"}
    }
]

# ChromaDB 클라이언트 초기화
@st.cache_resource
def init_chroma_client():
    if not USE_CHROMADB:
        return None
    
    try:
        # 가장 간단한 방법으로 시도
        client = chromadb.Client()
        return client
    except:
        return None

# 간단한 검색 함수 (ChromaDB 없이)
def simple_search(query, data=SAMPLE_DATA):
    """키워드 기반 간단한 검색"""
    query_lower = query.lower()
    results = []
    
    for item in data:
        score = 0
        content_lower = item["content"].lower()
        title_lower = item["title"].lower()
        
        # 키워드 매칭
        keywords = query_lower.split()
        for keyword in keywords:
            if keyword in content_lower:
                score += 2
            if keyword in title_lower:
                score += 3
            if keyword in str(item["metadata"]).lower():
                score += 1
        
        if score > 0:
            results.append((score, item))
    
    # 점수 순으로 정렬
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:3]]

# 벡터 데이터베이스 검색 함수
def search_vector_db(collection, query, n_results=20):
    # ChromaDB를 사용할 수 없거나 collection이 없으면 간단한 검색 사용
    if not USE_CHROMADB or not collection:
        return simple_search(query)
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count())
        )
        
        documents = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                document = {
                    "content": results['documents'][0][i],
                    "title": results['metadatas'][0][i].get('title', '제목 없음'),
                    "metadata": results['metadatas'][0][i]
                }
                documents.append(document)
        
        return documents if documents else simple_search(query)
    except Exception as e:
        st.sidebar.warning(f"벡터 검색 실패, 키워드 검색 사용: {e}")
        return simple_search(query)

# 컬렉션 가져오기
def get_collection(collection_name):
    if not USE_CHROMADB:
        return None
    
    try:
        client = init_chroma_client()
        if not client:
            return None
        
        # 기존 컬렉션 확인
        existing_collections = [col.name for col in client.list_collections()]
        
        if collection_name in existing_collections:
            return client.get_collection(name=collection_name)
        else:
            # 새 컬렉션 생성 시도
            try:
                collection = client.create_collection(name=collection_name)
                # 샘플 데이터 추가
                for i, data in enumerate(SAMPLE_DATA):
                    collection.add(
                        documents=[data["content"]],
                        metadatas=[data["metadata"]],
                        ids=[f"doc_{i}"]
                    )
                return collection
            except:
                return None
    except:
        return None

# OpenAI를 활용한 응답 생성 함수
def get_gpt_response(query, search_results, api_key, model="gpt-4o-mini"):
    if not api_key:
        return "OpenAI API 키가 설정되지 않았습니다."

    try:
        client = OpenAI(api_key=api_key.strip())
        
        # 컨텍스트 구성
        context = "다음은 부동산 가격 관련 데이터입니다:\n\n"
        
        for i, result in enumerate(search_results):
            context += f"문서 {i+1}:\n"
            context += f"제목: {result.get('title', '제목 없음')}\n"
            
            if result.get('metadata'):
                metadata = result['metadata']
                for key, value in metadata.items():
                    context += f"{key}: {value}\n"
            
            context += f"내용: {result['content']}\n\n"
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 부동산 시장 전문가입니다. 제공된 데이터를 바탕으로 정확하고 간결하게 답변하세요."},
                {"role": "user", "content": f"{context}\n질문: {query}"}
            ],
            temperature=0.5,
            max_tokens=800
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"응답 생성 중 오류: {str(e)}"

# 간단한 응답 생성
def get_simple_response(query, search_results):
    if not search_results:
        return "관련 데이터를 찾을 수 없습니다."
    
    result_text = f"'{query}'에 대한 검색 결과:\n\n"
    
    for i, result in enumerate(search_results[:3]):
        result_text += f"**{result.get('title', f'문서 {i+1}')}**\n"
        content = result['content']
        if len(content) > 150:
            content = content[:150] + "..."
        result_text += f"{content}\n\n"
    
    return result_text

# 챗봇 응답 생성 함수
def chat_response(question, collection):
    # 검색 수행
    search_results = search_vector_db(collection, question)
    
    # API 키가 있으면 GPT 사용, 없으면 간단한 응답
    if api_key:
        return get_gpt_response(question, search_results, api_key)
    else:
        return get_simple_response(question, search_results)

# 컬렉션 가져오기
collection = get_collection(collection_name) if USE_CHROMADB else None

# 상태 표시
if USE_CHROMADB and collection:
    st.sidebar.success(f"✅ ChromaDB 컬렉션 '{collection_name}' 사용 중")
else:
    st.sidebar.info("📝 간단한 키워드 검색 모드로 실행 중")

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

    # 사용자 메시지를 대화 이력에 저장
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # 응답 생성
    with st.spinner("답변을 준비하고 있습니다..."):
        response = chat_response(prompt, collection)

    # 응답 메시지 표시
    with st.chat_message("assistant"):
        st.markdown(response)

    # AI 응답을 대화 이력에 저장
    st.session_state.chat_history.append({"role": "assistant", "content": response})

# 사이드바 예시 질문
st.sidebar.header("예시 질문")
example_questions = [
    "서울 강남 아파트 가격 동향은?",
    "최근 전세 시장 변화는?",
    "부동산 정책의 영향은?",
    "송파구와 강남구 비교"
]

# 예시 질문 버튼
for i, question in enumerate(example_questions):
    if st.sidebar.button(question, key=f"ex_{i}"):
        st.session_state.chat_history.append({"role": "user", "content": question})
        response = chat_response(question, collection)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

# 대화 기록 초기화 버튼
if st.sidebar.button("대화 기록 초기화"):
    st.session_state.chat_history = []
    st.rerun()
