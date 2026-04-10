from langchain_core.messages import SystemMessage

from core.state import AgenticWorkflowState
from tools.search_engine import execute_tavily_search


OFFICIAL_DOMAIN_HINTS = {
    "Samsung": "site:news.samsung.com OR site:semiconductor.samsung.com",
    "Micron": "site:micron.com OR site:investors.micron.com",
    "SK hynix": "site:news.skhynix.com OR site:skhynix.com",
}


def _build_queries(competitors: list[str], techs: list[str]) -> list[str]:
    queries: list[str] = []

    for company in competitors:
        domain_hint = OFFICIAL_DOMAIN_HINTS.get(company, "")
        for tech_name in techs:
            # 공식 출처 우선: reference 품질과 링크 정확도를 높이기 위한 쿼리
            queries.append(f"{domain_hint} {company} {tech_name} official announcement")
            queries.append(f"{domain_hint} {company} {tech_name} product page specification")

            # 반대 근거/기술 한계/검증 신호를 함께 탐색
            queries.append(f"{company} {tech_name} yield thermal power customer validation")
            queries.append(f"{company} {tech_name} limitation issue drawback benchmark")
            queries.append(f"{company} {tech_name} patent hiring conference news")

    # SK hynix 관점 전략 비교를 위해 자사 공식 정보도 같이 수집
    sk_domain = OFFICIAL_DOMAIN_HINTS["SK hynix"]
    queries.extend(
        [
            f"{sk_domain} SK hynix HBM4 official",
            f"{sk_domain} SK hynix AiMX official",
            f"{sk_domain} SK hynix CXL official customer validation",
        ]
    )

    # 중복 제거하면서 순서 유지
    deduped_queries: list[str] = []
    seen = set()
    for query in queries:
        normalized = " ".join(query.split())
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped_queries.append(normalized)
    return deduped_queries


def web_search_agent(state: AgenticWorkflowState):
    """Web Search Agent: 기술별/경쟁사별 공식 출처 우선 다중 쿼리 검색"""
    print("🌐 [Web Search Agent] 실행 중...")
    print("📥 [Supervisor -> Web Search Agent] 검색 질의 생성 및 교차 검증용 웹 자료 수집을 시작합니다.")
    scope = state["global_info"].get("analysis_scope", {})
    competitors = scope.get("competitors", ["Samsung", "Micron"])
    techs = scope.get("tech", ["HBM4", "PIM", "CXL"])

    search_queries = _build_queries(competitors, techs)
    print(f"🧭 [Web Search Agent] 생성된 검색 질의 수: {len(search_queries)}")

    feedback = (
        state["global_info"]["messages"][-1].content
        if state["supervisor_ctrl"]["revision_count"] > 0
        else ""
    )
    if "Supervisor 반려" in feedback:
        clean_feedback = feedback.replace("Supervisor 반려: ", "").strip()
        # 출처/웹자료가 부족한 경우 재검색 쿼리도 더 직접적으로 추가
        search_queries.extend(
            [
                f"official source reference link {clean_feedback[:120]}",
                f"press release pdf specification {clean_feedback[:120]}",
            ]
        )

    web_results = execute_tavily_search(search_queries)

    new_state = state.copy()
    new_state["retrieval_data"]["web_raw_results"] = web_results
    # 웹 검색을 다시 탄 경우에는 새 자료 기반으로 초안을 다시 생성하도록 비운다.
    new_state["draft_work"]["current_draft"] = ""
    print(f"[Web Search Agent -> Supervisor] 웹 검색 결과 {len(web_results)}건을 전달합니다.")
    new_state["global_info"]["messages"].append(
        SystemMessage(content=f"웹 검색이 완료되었습니다. 수집 문서 수: {len(web_results)}")
    )
    return new_state
