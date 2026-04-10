## BGE-M3 임베딩과 FAISS + BM25 하이브리드 검색 세팅입니다. data/ 폴더에 PDF를 넣으면 알아서 읽어오도록 구성

import hashlib
import os
import re
import pickle
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class FallbackHashEmbeddings(Embeddings):
    """추가 모델 다운로드 없이 동작하는 경량 임베딩 폴백."""

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = sum(value * value for value in vector) ** 0.5
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def _resolve_data_dir(data_dir: str) -> Path:
    data_path = Path(data_dir)
    if data_path.is_absolute():
        return data_path
    project_root = Path(__file__).resolve().parent.parent
    return project_root / data_path


def _build_embeddings() -> Embeddings:
    try:
        return HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
    except Exception as exc:
        print(f"⚠️ [Retriever] BGE-M3 로드 실패. 해시 임베딩으로 폴백합니다: {exc}")
        return FallbackHashEmbeddings()


def setup_rag_retriever(data_dir: str = "data"):
    """BGE-M3 기반 Hybrid Search Retriever 세팅 (캐싱 기능 포함)"""
    print("⚙️ [Retriever] RAG 엔진 세팅 중 (BGE-M3)...")
    embeddings = _build_embeddings()
    resolved_data_dir = _resolve_data_dir(data_dir)

    # 💾 저장할 캐시 폴더 경로 설정
    cache_dir = Path("db_cache")
    faiss_path = cache_dir / "faiss_index"
    bm25_path = cache_dir / "bm25_index.pkl"

    # 1. 저장된 DB가 있으면 1초 만에 불러오기
    if faiss_path.exists() and bm25_path.exists():
        print("⚡ [Retriever] 기존에 저장된 로컬 DB를 1초 만에 불러옵니다!")
        faiss_db = FAISS.load_local(str(faiss_path), embeddings, allow_dangerous_deserialization=True)
        with open(bm25_path, "rb") as f:
            bm25_retriever = pickle.load(f)

    # 2. 저장된 DB가 없으면 새로 만들고 저장하기
    else:
        print("⏳ [Retriever] 저장된 DB가 없습니다. 최초 1회 문서 로드를 시작합니다...")
        docs = []
        if resolved_data_dir.exists():
            for filename in os.listdir(resolved_data_dir):
                if filename.endswith(".pdf"):
                    file_path = resolved_data_dir / filename
                    # [수정 2] str()로 감싸서 확실하게 에러 방지
                    loader = PyMuPDFLoader(str(file_path)) 
                    docs.extend(loader.load())
                    print(f"📄 로드 완료: {filename}")

        if not docs:
            print("⚠️ [Warning] data 폴더에 PDF가 없습니다. 기본 더미 데이터를 사용합니다.")
            dummy_texts = [
                "HBM4는 16단 적층을 목표로 하며, 발열 제어를 위해 하이브리드 본딩이 필수적이다.",
                "PIM 기술인 SK하이닉스의 AiMX는 GDDR6-AiM을 활용하여 LLM 추론 성능을 대폭 높인다.",
                "CXL 3.0은 메모리 풀링을 지원하여 데이터센터의 확장성을 극대화한다."
            ]
            faiss_db = FAISS.from_texts(dummy_texts, embeddings)
            bm25_retriever = BM25Retriever.from_texts(dummy_texts)
        else:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            split_docs = text_splitter.split_documents(docs)
            faiss_db = FAISS.from_documents(split_docs, embeddings)
            bm25_retriever = BM25Retriever.from_documents(split_docs)

            print("💾 [Retriever] 임베딩 완료! 디스크에 안전하게 저장합니다...")
            cache_dir.mkdir(exist_ok=True)
            faiss_db.save_local(str(faiss_path))
            with open(bm25_path, "wb") as f:
                pickle.dump(bm25_retriever, f)

    # [수정 3] 검색기 설정 (비용과 품질의 밸런스를 위해 6으로 세팅)
    faiss_retriever = faiss_db.as_retriever(search_kwargs={"k": 6})
    bm25_retriever.k = 6
    
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.4, 0.6]
    )
    
    print("✅ [Retriever] 세팅 완료!")
    return ensemble_retriever