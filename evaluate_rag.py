from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from tools.retriever import setup_rag_retriever


DEFAULT_K_VALUES = (1, 3, 5)


# 질문마다 정답 문서를 1개 이상 허용한다.
# source 메타데이터는 절대경로일 수 있으므로 파일명 기준으로 비교한다.
EVAL_DATASET = [
    {
        "query": "삼성전자 HBM4 양산과 발열 제어 기술",
        "answers": ["hbm4.pdf"],
    },
    {
        "query": "SK하이닉스 HBM4 로드맵과 대역폭 경쟁력",
        "answers": ["hbm4.pdf", "JEPsk.pdf"],
    },
    {
        "query": "CXL 기반 메모리 확장 솔루션과 적용 방향",
        "answers": ["CXL.pdf"],
    },
    {
        "query": "JEDEC 메모리 표준 규격과 핀 배열 정보",
        "answers": ["JEP30-E100I.pdf"],
    },
    {
        "query": "삼성전자 메모리 전략과 HBM 관련 비교 자료",
        "answers": ["JEPsamsung.pdf", "hbm4.pdf"],
    },
]


@dataclass
class QueryResult:
    query: str
    expected_docs: list[str]
    retrieved_docs: list[str]
    first_relevant_rank: int | None

    def hit_at(self, k: int) -> int:
        return int(self.first_relevant_rank is not None and self.first_relevant_rank <= k)

    def reciprocal_rank_at(self, k: int) -> float:
        if self.first_relevant_rank is None or self.first_relevant_rank > k:
            return 0.0
        return 1.0 / self.first_relevant_rank


def _normalize_doc_name(source: str) -> str:
    return os.path.basename(source).strip()


def _unique_doc_names(docs: Iterable) -> list[str]:
    unique_docs: list[str] = []
    seen = set()

    for doc in docs:
        source = _normalize_doc_name(doc.metadata.get("source", ""))
        if not source or source in seen:
            continue
        seen.add(source)
        unique_docs.append(source)

    return unique_docs


def _first_relevant_rank(retrieved_docs: list[str], expected_docs: set[str]) -> int | None:
    for index, doc_name in enumerate(retrieved_docs, start=1):
        if doc_name in expected_docs:
            return index
    return None


def evaluate_retriever(k_values: tuple[int, ...] = DEFAULT_K_VALUES) -> tuple[dict, list[QueryResult]]:
    print("🔍 Retrieval 성능 평가를 시작합니다...")
    retriever = setup_rag_retriever("data")

    query_results: list[QueryResult] = []
    max_k = max(k_values)

    print("\n" + "-" * 80)
    for item in EVAL_DATASET:
        query = item["query"]
        expected_docs = {_normalize_doc_name(name) for name in item["answers"]}
        docs = retriever.invoke(query)
        retrieved_docs = _unique_doc_names(docs)[:max_k]
        rank = _first_relevant_rank(retrieved_docs, expected_docs)

        result = QueryResult(
            query=query,
            expected_docs=sorted(expected_docs),
            retrieved_docs=retrieved_docs,
            first_relevant_rank=rank,
        )
        query_results.append(result)

        rank_text = rank if rank is not None else "N/A"
        print(f"Q: {query}")
        print(f" - Expected: {', '.join(result.expected_docs)}")
        print(f" - Retrieved: {', '.join(result.retrieved_docs) if result.retrieved_docs else '없음'}")
        print(f" - First Relevant Rank: {rank_text}")
        print("-" * 80)

    summary = {
        "num_queries": len(query_results),
        "metrics": {},
    }

    for k in k_values:
        hit_rate = sum(result.hit_at(k) for result in query_results) / len(query_results)
        mrr = sum(result.reciprocal_rank_at(k) for result in query_results) / len(query_results)
        summary["metrics"][f"hit_rate@{k}"] = round(hit_rate, 4)
        summary["metrics"][f"mrr@{k}"] = round(mrr, 4)

    return summary, query_results


def build_markdown_summary(summary: dict) -> str:
    lines = [
        "## Retrieval Evaluation",
        "",
        f"- Number of evaluation queries: {summary['num_queries']}",
    ]

    for metric_name, value in summary["metrics"].items():
        pretty_percent = value * 100 if metric_name.startswith("hit_rate@") else value
        if metric_name.startswith("hit_rate@"):
            lines.append(f"- {metric_name.upper()}: {pretty_percent:.1f}%")
        else:
            lines.append(f"- {metric_name.upper()}: {pretty_percent:.3f}")

    return "\n".join(lines)


def save_outputs(summary: dict, query_results: list[QueryResult], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "retrieval_metrics.json"
    results_path = output_dir / "retrieval_query_results.json"
    markdown_path = output_dir / "retrieval_metrics.md"

    metrics_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    results_path.write_text(
        json.dumps([asdict(result) for result in query_results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(build_markdown_summary(summary), encoding="utf-8")

    print(f"📁 metrics saved: {metrics_path}")
    print(f"📁 query results saved: {results_path}")
    print(f"📁 markdown summary saved: {markdown_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality with Hit Rate@K and MRR@K.")
    parser.add_argument(
        "--save-dir",
        default="output",
        help="평가 결과를 저장할 디렉터리 경로",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary, query_results = evaluate_retriever()

    print("\n" + "=" * 80)
    print("📊 Retrieval Evaluation Summary")
    for metric_name, value in summary["metrics"].items():
        if metric_name.startswith("hit_rate@"):
            print(f" - {metric_name}: {value * 100:.1f}%")
        else:
            print(f" - {metric_name}: {value:.3f}")
    print("=" * 80)

    markdown_summary = build_markdown_summary(summary)
    print("\nREADME에 바로 넣을 수 있는 요약:")
    print(markdown_summary)

    save_outputs(summary, query_results, Path(args.save_dir))


if __name__ == "__main__":
    main()
