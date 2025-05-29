# 대화형 쳇봇 애플리케이션에 필요한 라이브러리 임포트
import streamlit as st
import json
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
import re

# 페이지 설정
st.set_page_config(page_title="부동산 가격 분석 AI 에이전트", page_icon="🏠")

# OpenAI API 키 가져오기
def get_api_key():
    """Streamlit secrets 또는 사이드바 입력에서 API 키 가져오기"""
    # 1. Streamlit secrets에서 먼저 확인
    try:
        return st.secrets["OPENAI_API_KEY"]
    except:
        # 2. secrets가 없으면 사이드바 입력 사용
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

# 컬렉션 이름 입력 (사이드바)
collection_name = st.sidebar.text_input("사용할 컬렉션 이름", value="real_estate_prices_20250511")

# 페이지 제목
st.title("🏠 부동산 가격 분석 AI 데이터 분석가")
st.write("뉴스 기사 및 보고서에서 수집한 부동산 가격 데이터에 대해 질문해보세요.")

# 이미지 표시 (옵션)
try:
    st.image("realestate.png", use_container_width=True)
except:
    # 이미지가 없어도 앱이 작동하도록 처리
    pass

# ChromaDB 클라이언트 초기화
@st.cache_resource
def init_chroma_client():
    # 메모리 모드로 사용 (더 간단!)
    return chromadb.Client()

# 샘플 데이터 로드 함수 (데모용)
def load_sample_data(client):
    """데모를 위한 샘플 데이터 로드"""
    try:
        collection = client.create_collection(
            name="real_estate_prices_20250511",
            metadata={"description": "부동산 가격 분석 데이터"}
        )
        
        # 샘플 데이터
        sample_docs = [
            {
                "doc": "서울 강남구 아파트 평균 매매가격이 전월 대비 2.3% 상승했습니다. 특히 대치동과 삼성동 일대의 대단지 아파트를 중심으로 가격 상승세가 뚜렷하게 나타났습니다.",
                "metadata": {"region": "강남구", "date": "2025-01", "price_trend": "상승", "article_type": "시장분석"}
            },
            {
                "doc": "송파구 잠실 일대 전세 가격이 안정세를 보이고 있습니다. 신규 아파트 공급과 함께 전세 수요가 분산되면서 가격 상승폭이 둔화되었습니다.",
                "metadata": {"region": "송파구", "date": "2025-01", "price_trend": "안정", "article_type": "시장분석"}
            },
            {
                "doc": "정부의 부동산 규제 완화 정책 발표 이후 서울 주요 지역의 거래량이 증가하고 있습니다. 특히 강남 3구를 중심으로 매수 문의가 늘어나고 있습니다.",
                "metadata": {"region": "서울", "date": "2025-01", "price_trend": "거래증가", "article_type": "정책분석"}
            }
        ]
        
        collection.add(
            documents=[item["doc"] for item in sample_docs],
            metadatas=[item["metadata"] for item in sample_docs],
            ids=[f"doc_{i}" for i in range(len(sample_docs))]
        )
        
        return collection
    except:
        # 이미 존재하는 경우
        return client.get_collection(name="real_estate_prices_20250511")

# 벡터 데이터베이스에서 컬렉션 가져오기
def get_collection(collection_name):
    try:
        client = init_chroma_client()
        
        # 컬렉션 목록 확인
        existing_collections = [col.name for col in client.list_collections()]
        
        if collection_name in existing_collections:
            collection = client.get_collection(name=collection_name)
        else:
            # 샘플 데이터로 새 컬렉션 생성
            st.sidebar.info(f"'{collection_name}' 컬렉션이 없어 샘플 데이터로 생성합니다.")
            collection = load_sample_data(client)
        
        return collection
    except Exception as e:
        st.sidebar.error(f"컬렉션 가져오기 오류: {e}")
        return None

# 벡터 데이터베이스 검색 함수
def search_vector_db(collection, query, n_results=20):
    try:
        if not collection:
            return [{"content": "컬렉션을 불러올 수 없습니다. 컬렉션 이름을 확인하세요.", "title": "오류", "metadata": {}}]
        
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
        
        return documents
    except Exception as e:
        st.sidebar.error(f"검색 오류: {e}")
        return [{"content": f"검색 중 오류 발생: {e}", "title": "오류", "metadata": {}}]

# OpenAI를 활용한 응답 생성 함수
def get_gpt_response(query, search_results, api_key, model="gpt-4o-mini"):
    if not api_key:
        return "OpenAI API 키가 설정되지 않았습니다. Streamlit Cloud Settings에서 Secrets를 설정하거나 사이드바에서 API 키를 입력해주세요."

    try:
        # OpenAI 클라이언트 초기화
        api_key = api_key.strip().replace('\ufeff', '')
        client = OpenAI(api_key=api_key)
        
        # 컨텍스트 구성
        context = "다음은 뉴스 기사와 보고서에서 수집한 부동산 가격 관련 데이터입니다:\n\n"
        
        for i, result in enumerate(search_results):
            context += f"문서 {i+1}:\n"
            context += f"제목: {result['title']}\n"
            
            # 메타데이터 추가
            if result['metadata']:
                metadata = result['metadata']
                if 'date' in metadata:
                    context += f"작성일: {metadata['date']}\n"
                if 'region' in metadata:
                    context += f"지역: {metadata['region']}\n"
                if 'price_trend' in metadata:
                    context += f"가격 동향: {metadata['price_trend']}\n"
                if 'article_type' in metadata:
                    context += f"기사 유형: {metadata['article_type']}\n"
            
            # 내용 요약 (너무 길면 잘라냄)
            content = result['content']
            if len(content) > 8000:
                content = content[:8000] + "..."
            context += f"내용: {content}\n\n"
        
        # 개선된 GPT 프롬프트
        system_prompt = """당신은 부동산 시장 및 가격 분석 전문가입니다. 제공된 문서들을 바탕으로 사용자 질문에
        정확하고 간결하게 답변해주세요.

        답변 작성 가이드라인:
        1. 사용자의 질문에 직접적으로 관련된 내용만 답변하세요.
        2. 부동산 가격 동향, 지역별 시세, 가격 변동 요인 등에 대해 정확한 정보를 제공하세요.
        3. 제공된 문서에 확인할 수 있는 사실에 기반하여 답변하세요.
        4. 답변은 간결하고 명확하게 작성하세요.
        5. 부동산 투자 조언이나 법적 조언을 제공하지 마세요.
        """

        user_prompt = f"""{context}

        사용자 질문: {query}

        위 문서들을 분석하여 사용자의 질문에만 직접적으로 답변해주세요.
        질문에 관련된 정보만 제공하고, 불필요한 배경설명이나 추가 정보는 생략해주세요.
        """
                
        # API 호출
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=800
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        
        # 인증 오류 확인
        if "auth" in error_msg.lower() or "api key" in error_msg.lower():
            return "OpenAI API 키 인증에 실패했습니다. API 키를 확인해주세요."
        else:
            return f"분석 중 오류가 발생했습니다: {error_msg}"

# 부동산과 관련없는 질문을 했을때 간단한 응답을 반환하는 함수
def get_simple_response(query, search_results):
    if not search_results or search_results[0].get("title") == "오류":
        return "관련 데이터를 찾을 수 없습니다."
    
    result_text = f"'{query}'에 대한 검색 결과:\n\n"
    
    for i, result in enumerate(search_results[:3]):  # 최대 3개만 표시
        result_text += f"**문서 {i+1}:** {result['title']}\n"
        
        # 내용 요약 (100자로 제한)
        content = result['content']
        if len(content) > 100:
            content = content[:100] + "..."
        result_text += f"{content}\n\n"
    
    result_text += "더 자세한 분석을 위해서는 OpenAI API 키를 설정해주세요."
    return result_text

# 챗봇 응답 생성 함수
def chat_response(question, collection):
    # 벡터 데이터베이스 검색
    search_results = search_vector_db(collection, question)
    
    # ChatGPT API 키가 있으면 GPT 사용, 없으면 간단한 응답
    if api_key:
        return get_gpt_response(question, search_results, api_key)
    else:
        return get_simple_response(question, search_results)

# 컬렉션 가져오기
collection = get_collection(collection_name)

# 컬렉션 정보 표시
if collection:
    try:
        count = collection.count()
        st.sidebar.success(f"✅ 컬렉션 '{collection_name}'에서 {count}개의 문서를 불러왔습니다.")
    except Exception as e:
        st.sidebar.warning(f"컬렉션 정보 확인 중 오류: {e}")
else:
    st.sidebar.warning(f"⚠️ 컬렉션 '{collection_name}'을 찾을 수 없습니다.")

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
    with st.spinner("질문과 관련된 부동산 정보를 수집하여 답변을 준비하고 있는 중..."):
        response = chat_response(prompt, collection)

    # 응답 메시지 표시
    with st.chat_message("assistant"):
        st.markdown(response)

    # AI 응답을 대화 이력에 저장
    st.session_state.chat_history.append({"role": "assistant", "content": response})

# 사이드바 예시 질문
st.sidebar.header("예시 질문")
example_questions = [
    "서울 강남 아파트 가격 동향은 어떻게 되나요?",
    "최근 전세 시장의 변화 추이를 알려주세요.",
    "어떤 정책이 부동산 가격에 가장 큰 영향을 미쳤나요?",
    "지방 부동산 시장은 서울과 비교하여 어떤 상황인가요?",
    "부동산 가격 상승의 주요 원인은 무엇인가요?",
    "송파구와 강남구의 아파트 가격을 비교해주세요."
]

# 예시 질문 버튼
for question in example_questions:
    if st.sidebar.button(question, key=f"ex_{question[:10]}"):
        # 사용자 메시지 표시 및 저장
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_history.append({"role": "user", "content": question})

        # 응답 생성
        with st.spinner("질문과 관련된 부동산 정보를 수집하여 분석하고 있는 중..."):
            response = chat_response(question, collection)

        # 응답 메시지 표시 및 저장
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})

        # 페이지 새로고침
        st.rerun()

# 데이터 시각화 섹션 추가
st.sidebar.header("데이터 시각화")
if st.sidebar.button("가격 동향 차트 보기"):
    st.session_state.show_chart = True

# 데이터 분석 결과를 보여주는 차트 (예시)
if "show_chart" in st.session_state and st.session_state.show_chart:
    st.subheader("주요 지역 부동산 가격 동향")
    st.line_chart({
        "강남": [100, 105, 110, 108, 115, 120],
        "송파": [90, 95, 100, 103, 107, 110],
        "마포": [80, 82, 85, 87, 90, 92]
    })
    st.caption("최근 6개월 부동산 가격 지수 (기준점: 100)")

# 대화 기록 초기화 버튼
if st.sidebar.button("대화 기록 초기화"):
    st.session_state.chat_history = []
    st.rerun()

# 컬렉션 목록 표시
try:
    client = init_chroma_client()
    collections = client.list_collections()
    
    with st.sidebar.expander("사용 가능한 컬렉션 목록"):
        if collections:
            for coll in collections:
                st.write(f"- {coll.name}")
        else:
            st.write("사용 가능한 컬렉션이 없습니다.")
except Exception as e:
    st.sidebar.error(f"컬렉션 목록 로드 오류: {e}")
