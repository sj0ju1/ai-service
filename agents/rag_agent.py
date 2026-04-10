import os
from langchain_core.messages import SystemMessage
from core.state import AgenticWorkflowState
from tools.retriever import setup_rag_retriever

print("RAG 모델 초기화 중... (최초 1회만 실행됩니다)")
retriever_instance = setup_rag_retriever("data")

def rag_agent(state: AgenticWorkflowState):
    """RAG Agent: 문서 추출 및 터미널 출처 로깅 기능 포함"""
    print("[RAG Agent] 문서 추출 중...")
    print("[Supervisor -> RAG Agent] 내부 PDF 문서 검색을 시작합니다.")
    query = state["global_info"]["query"]
    
    # 문서 검색 실행
    docs = retriever_instance.invoke(query)
    
    rag_results = []
    
    # 터미널에서 개발자가 보기 편하게 UI 꾸미기
    print("\n" + "="*50)
    print("🔍 [RAG 엔진이 찾아낸 문서 조각(Chunk) 출처]")
    
    for i, doc in enumerate(docs):
        # 메타데이터에서 파일 경로를 빼오고, 깔끔하게 파일명만 남김
        source_path = doc.metadata.get('source', '알 수 없는 문서')
        filename = os.path.basename(source_path)
        
        # 1. 터미널에 출력 (개발자 확인용)
        print(f"  📍 Chunk {i+1}: [{filename}] 에서 발췌됨")
        
        # 2. 다음 에이전트(Draft)에게 넘겨줄 텍스트에도 꼬리표 달기
        chunk_text = f"[출처: {filename}] {doc.page_content}"
        rag_results.append(chunk_text)
        
    print("="*50 + "\n")
    print(f"📨 [RAG Agent -> Supervisor] 문서 조각 {len(rag_results)}개를 전달합니다.")
    
    new_state = state.copy()
    new_state["retrieval_data"]["rag_raw_chunks"] = rag_results
    new_state["global_info"]["messages"].append(SystemMessage(content="RAG 검색이 완료되었습니다."))
    return new_state
