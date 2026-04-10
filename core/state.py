from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# 1. Global State (전역 상태 및 대화 히스토리)
class GlobalState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    analysis_scope: Dict[str, Any]
    final_report: str
    workflow_status: str

# 2. Supervisor State (부장님의 제어 상태)
class SupervisorState(TypedDict):
    next_agent: str
    revision_count: int
    missing_info_log: List[str]

# 3. Retrieval State (검색 데이터 수집 상태)
class RetrievalState(TypedDict):
    rag_raw_chunks: List[str]
    web_raw_results: List[str]

# 4. Draft State (보고서 초안 작성 상태)
class DraftState(TypedDict):
    current_draft: str
    trl_justification: str

# 5. Master State (LangGraph 메인 상태)
class AgenticWorkflowState(TypedDict):
    global_info: GlobalState
    supervisor_ctrl: SupervisorState
    retrieval_data: RetrievalState
    draft_work: DraftState