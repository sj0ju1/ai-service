import re
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from core.state import AgenticWorkflowState


class SupervisorDecision(BaseModel):
    next_node: str = Field(description="'draft_agent' 또는 승인 시 'formatting_node'")
    feedback: str = Field(description="반려 시 하위 에이전트에게 전달할 구체적 수정 지시")


NODE_LABELS = {
    "web_search_agent": "Web Search Agent",
    "rag_agent": "RAG Agent",
    "draft_agent": "Draft Agent",
    "formatting_node": "Formatting Node",
}


def _normalize_draft(draft):
    if hasattr(draft, "content"):
        return draft.content
    if isinstance(draft, dict):
        return draft.get("content", str(draft))
    if not isinstance(draft, str):
        return str(draft)
    return draft


def _count_references(draft: str) -> int:
    ref_section_match = re.search(r"##\s*\d+\.\s*REFERENCE(.*)", draft, re.DOTALL)
    if not ref_section_match:
        return 0

    ref_section = ref_section_match.group(1)

    url_count = len(re.findall(r"https?://\S+", ref_section))
    bullet_count = len(re.findall(r"^\s*[-*]\s+", ref_section, re.MULTILINE))

    return max(url_count, bullet_count)


def _has_reference_urls(draft: str) -> bool:
    ref_section_match = re.search(r"##\s*\d+\.\s*REFERENCE(.*)", draft, re.DOTALL)
    if not ref_section_match:
        return False
    ref_section = ref_section_match.group(1)
    return bool(re.search(r"https?://\S+", ref_section))


def _has_markdown_table(draft: str) -> bool:
    return "|" in draft and "---" in draft


def _contains_any(draft: str, keywords: list[str]) -> bool:
    return any(keyword in draft for keyword in keywords)


def _route_with_log(state: AgenticWorkflowState, target: str, reason: str) -> None:
    state["supervisor_ctrl"]["next_agent"] = target
    target_label = NODE_LABELS.get(target, target)
    print(f"📨 [Supervisor -> {target_label}] {reason}")


def supervisor_agent(state: AgenticWorkflowState):
    """Supervisor: 라우팅, 품질 검증 및 제약 조건 통제"""
    print("👔 [Supervisor] 워크플로우 통제 및 검증 중...")

    # 1. 데이터 수집 단계 라우팅
    if not state["retrieval_data"]["web_raw_results"]:
        _route_with_log(state, "web_search_agent", "웹 검색 결과가 비어 있어 자료 수집을 요청합니다.")
        return state

    if not state["retrieval_data"]["rag_raw_chunks"]:
        _route_with_log(state, "rag_agent", "RAG 문서 조각이 비어 있어 내부 문서 검색을 요청합니다.")
        return state

    if not state["draft_work"]["current_draft"]:
        _route_with_log(state, "draft_agent", "수집된 자료를 바탕으로 초안 작성을 요청합니다.")
        return state

    # 2. 재시도 제한
    revision_count = state["supervisor_ctrl"]["revision_count"]
    if revision_count >= 2:
        print("⚠️ [Supervisor] 최대 재시도 도달. 강제 포맷팅 진행 (Fallback).")
        _route_with_log(state, "formatting_node", "재시도 한도에 도달해 현재 초안을 포맷팅 단계로 넘깁니다.")
        return state

    draft = _normalize_draft(state["draft_work"]["current_draft"])
    print("📥 [Draft Agent -> Supervisor] 보고서 초안을 전달받아 구조 및 품질 검증을 시작합니다.")

    # 3. Rule-based 구조 검증
    has_table = _has_markdown_table(draft)
    has_limit_section = "## 4. 분석 한계" in draft
    has_trl_limit = "TRL 4~6" in draft and "추정" in draft
    has_indirect_indicators = _contains_any(draft, ["특허", "채용", "간접 지표", "학회 발표"])
    has_source_column = "주요 출처" in draft
    has_samsung = _contains_any(draft, ["Samsung", "삼성", "삼성전자"])
    has_micron = "Micron" in draft
    tech_count = sum([1 for tech in ["HBM", "PIM", "CXL"] if tech in draft])
    has_additional_research_section = "추가 조사 필요 영역" in draft
    has_public_limit_section = "공개 정보 한계로 판단 어려운 항목" in draft
    has_priority_rationale = "왜 지금 이 순서인가" in draft
    ref_count = _count_references(draft)
    has_reference_urls = _has_reference_urls(draft)

    structural_errors = []

    if not has_table:
        structural_errors.append("HBM/PIM/CXL과 경쟁사를 비교하는 Markdown 표가 없습니다.")

    if not has_limit_section:
        structural_errors.append("'## 4. 분석 한계' 섹션이 없습니다.")

    if not has_trl_limit:
        structural_errors.append("'TRL 4~6' 및 '추정' 표현이 명시되지 않았습니다.")

    if not has_indirect_indicators:
        structural_errors.append("특허/채용/학회 발표 등 간접 지표 활용 근거가 없습니다.")

    if not has_source_column:
        structural_errors.append("비교 표에 '주요 출처' 컬럼이 없습니다.")

    if not (has_samsung and has_micron):
        structural_errors.append("Samsung과 Micron이 모두 비교 대상으로 충분히 반영되지 않았습니다.")

    if tech_count < 2:
        structural_errors.append("HBM, PIM, CXL 중 최소 2개 이상 기술 비교가 필요합니다.")

    if not has_additional_research_section:
        structural_errors.append("'추가 조사 필요 영역' 섹션이 없습니다.")

    if not has_public_limit_section:
        structural_errors.append("'공개 정보 한계로 판단 어려운 항목' 섹션이 없습니다.")

    if not has_priority_rationale:
        structural_errors.append("'왜 지금 이 순서인가'에 대한 설명이 없습니다.")

    if ref_count < 3:
        structural_errors.append("REFERENCE 섹션에 최소 3개 이상의 출처가 필요합니다.")

    if not has_reference_urls:
        structural_errors.append("REFERENCE 섹션에 실제 링크(URL) 포함 출처가 필요합니다.")

    if structural_errors:
        feedback = " / ".join(structural_errors)
        needs_fresh_web_search = any(
            keyword in feedback
            for keyword in ["REFERENCE", "출처", "링크", "주요 출처"]
        )
        needs_fresh_web_search = needs_fresh_web_search or any(
            keyword in feedback
            for keyword in [
                "Samsung과 Micron이 모두 비교 대상으로 충분히 반영되지 않았습니다.",
                "HBM, PIM, CXL 중 최소 2개 이상 기술 비교가 필요합니다.",
            ]
        )

        if needs_fresh_web_search:
            state["retrieval_data"]["web_raw_results"] = []
            state["draft_work"]["current_draft"] = ""
            _route_with_log(
                state,
                "web_search_agent",
                "출처/링크 근거가 부족해 웹 검색부터 다시 수행하도록 요청합니다.",
            )
        else:
            _route_with_log(
                state,
                "draft_agent",
                "초안 구조 보완이 필요해 수정 재작성을 요청합니다.",
            )
        state["supervisor_ctrl"]["revision_count"] += 1
        state["supervisor_ctrl"]["missing_info_log"].append(feedback)
        state["global_info"]["messages"].append(
            SystemMessage(content=f"Supervisor 반려: {feedback}")
        )
        print(f"🔄 [Supervisor 반려 - 구조 검증 실패] 사유: {feedback}")
        return state

    # 4. LLM 기반 품질 검증
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)

    validation_prompt = f"""
아래 보고서 초안을 검토하고, 다음 행동을 결정하세요.

[초안]
{draft}

판단 기준:
1. 문장 표현이 "해결했다", "완성했다", "압도적이다"처럼 단정적이지 않고 보수적인가?
2. 비교 표 이후의 해석 문단이 실제로 표를 설명하고 있는가?
3. 각 경쟁사에 대해 최소 1개 이상의 판단 근거가 자연스럽게 제시되는가?
4. 정보 부족을 숨기지 않고 "정보 부족", "공개 정보 한계", "추정 보류" 등으로 적절히 표현하는가?
5. SK하이닉스 관점의 전략적 시사점이 단기/중기 대응 방향으로 구분되어 있는가?
6. 전략적 시사점이 SK하이닉스 중심으로 구체적이며, 왜 지금 그 순서로 대응해야 하는지 설명하는가?
7. 추가 조사 필요 영역과 공개 정보 한계 항목이 분리되어 있는가?

승인 규칙:
- 구조적 요건은 이미 통과했으므로, 품질이 전반적으로 무난하면 'formatting_node'로 승인하세요.
- 일부 항목에 "정보 부족", "수율 파악 불가", "공개 정보 한계로 추정 보류"가 포함되어 있더라도,
  솔직한 한계 인정과 비교 구조가 유지되면 승인하세요.
- 정말 수정이 필요한 경우에만 'draft_agent'로 반려하고, 반드시 한 문장으로 구체적 수정 지시를 작성하세요.
"""

    decision = llm.with_structured_output(SupervisorDecision).invoke(
        [SystemMessage(content=validation_prompt)]
    )

    _route_with_log(state, decision.next_node, "LLM 품질 검증 결과에 따라 다음 단계를 지정합니다.")

    if decision.next_node != "formatting_node":
        if any(
            keyword in decision.feedback
            for keyword in ["출처", "REFERENCE", "링크", "Micron", "Samsung", "비교"]
        ):
            state["retrieval_data"]["web_raw_results"] = []
            state["draft_work"]["current_draft"] = ""
            _route_with_log(
                state,
                "web_search_agent",
                "품질 검증 중 출처 보강이 필요해 웹 검색 재수행을 요청합니다.",
            )
        state["supervisor_ctrl"]["revision_count"] += 1
        state["supervisor_ctrl"]["missing_info_log"].append(decision.feedback)
        state["global_info"]["messages"].append(
            SystemMessage(content=f"Supervisor 반려: {decision.feedback}")
        )
        print(f"[Supervisor 반려 - 품질 검증] 사유: {decision.feedback}")
    else:
        print("[Supervisor 승인] 기준 충족. 포맷팅 단계로 전달합니다.")

    return state
