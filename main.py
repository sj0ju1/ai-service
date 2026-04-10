import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

# 환경 변수 로드
load_dotenv()

# 핵심 State 및 Agent 임포트
from core.state import AgenticWorkflowState, GlobalState, SupervisorState, RetrievalState, DraftState
from agents.supervisor import supervisor_agent
from agents.web_agent import web_search_agent
from agents.rag_agent import rag_agent
from agents.draft_agent import draft_agent
from agents.formatting_node import formatting_node

def router(state: AgenticWorkflowState) -> str:
    """Supervisor가 지시한 노드로 이동"""
    return state["supervisor_ctrl"]["next_agent"]

def main():
    # 1. Graph 초기화
    workflow = StateGraph(AgenticWorkflowState)

    # 2. 노드 등록
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("web_search_agent", web_search_agent)
    workflow.add_node("rag_agent", rag_agent)
    workflow.add_node("draft_agent", draft_agent)
    workflow.add_node("formatting_node", formatting_node)

    # 3. 엣지(흐름) 연결 (Supervisor 패턴)
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges("supervisor", router)
    workflow.add_edge("web_search_agent", "supervisor")
    workflow.add_edge("rag_agent", "supervisor")
    workflow.add_edge("draft_agent", "supervisor")
    workflow.add_edge("formatting_node", END)

    # 4. 컴파일
    app = workflow.compile()

    # 5. 초기 State 주입
    initial_state = AgenticWorkflowState(
        global_info=GlobalState(
            messages=[HumanMessage(content="HBM4, PIM, CXL 최신 기술과 Samsung, Micron 전략 분석 보고서 작성해줘.")],
            query="HBM4, PIM, CXL 최신 기술과 Samsung, Micron 전략 분석 보고서 작성해줘.",
            analysis_scope={"competitors": ["Samsung", "Micron"], "tech": ["HBM4", "PIM", "CXL"]},
            final_report="",
            workflow_status="STARTED"
        ),
        supervisor_ctrl=SupervisorState(next_agent="", revision_count=0, missing_info_log=[]),
        retrieval_data=RetrievalState(rag_raw_chunks=[], web_raw_results=[]),
        draft_work=DraftState(current_draft="", trl_justification="")
    )

    print("\n🚀 미니 프로젝트 파이프라인 가동 시작!\n" + "="*50)
    # 6. 실행! (무한 루프 방지를 위해 recursion_limit 설정)
    for step, output in enumerate(app.stream(initial_state, {"recursion_limit": 15}), start=1):
        completed_nodes = ", ".join(output.keys())
        print(f"🧭 [Workflow] Step {step} 완료 노드: {completed_nodes}")
    
    print("="*50)
    print("✅ 워크플로우 실행이 완료되었습니다. output 폴더를 확인하세요.")

if __name__ == "__main__":
    main()
