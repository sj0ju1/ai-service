## Tavily API를 이용해 원문 내용까지 긁어오는 다중 쿼리 검색 로직

import os
from typing import List
from urllib.parse import urlparse
from tavily import TavilyClient


def execute_tavily_search(queries: List[str]) -> List[str]:
    """Tavily API를 활용한 다중 쿼리 교차 검색.

    검색 결과에는 제목, URL, 원본 쿼리를 함께 남겨서 초안 작성 시
    실제 reference 제목과 링크를 더 안정적으로 회수하도록 돕는다.
    """
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

    client = TavilyClient(api_key=tavily_api_key)
    results = []
    seen_urls = set()
    domain_counts: dict[str, int] = {}

    print(f"🔍 [Web Search] {len(queries)}개의 쿼리로 교차 검색을 시작합니다...")
    for q in queries:
        try:
            # include_raw_content=True 로 본문 텍스트까지 확보
            response = client.search(
                query=q,
                search_depth="advanced",
                include_raw_content=True,
                max_results=3
            )

            for result in response.get("results", []):
                url = result.get("url")
                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)
                title = result.get("title", "제목 없음")
                domain = urlparse(url).netloc or "unknown"
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                content = result.get("raw_content", result.get("content", ""))[:1200]
                print(f"   - [수집] {domain} | {title}")
                results.append(
                    "\n".join(
                        [
                            f"[검색 질의] {q}",
                            f"[출처 제목] {title}",
                            f"[출처 도메인] {domain}",
                            f"[출처 URL] {url}",
                            content,
                            "",
                        ]
                    )
                )

        except Exception as e:
            print(f"⚠️ 검색 중 에러 발생 (쿼리: {q}): {e}")

    if domain_counts:
        print("📊 [Web Search] 도메인별 수집 결과 요약")
        for domain, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"   - {domain}: {count}건")

    return results
