"""Módulo RAG Híbrido (Embeddings Gemini + BM25 Léxico) sobre o Manual de Políticas."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pypdf import PdfReader

from src.config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    POLICY_INDEX_CACHE_PATH,
    POLICY_PDF_PATH,
)
from src.database import normalize_text

PT_STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "era", "essa", "esse", "esta", "este", "eu", "foi", "ha",
    "isso", "ja", "la", "mais", "mas", "me", "meu", "minha", "na", "nas",
    "nao", "no", "nos", "num", "numa", "o", "os", "ou", "para", "pela",
    "pelas", "pelo", "pelos", "por", "qual", "quais", "quando", "que",
    "quem", "se", "sem", "ser", "seu", "sua", "suas", "seus", "so", "sobre",
    "tambem", "tem", "ter", "um", "uma", "umas", "uns", "voce", "voces",
}

TOP_SECTION_TITLES = [
    "1. Sobre a Empório da Música",
    "2. Horário de Funcionamento",
    "3. Formas de Pagamento",
    "4. Política de Trocas e Devoluções",
    "5. Política de Frete e Entregas",
    "6. Promoções e Descontos",
    "7. Atendimento via WhatsApp",
    "8. Garantia",
    "9. Privacidade e Proteção de Dados",
    "10. Disposições Finais",
]

SUBSECTION_PATTERN = re.compile(
    r"(?=(?:\b(?:10|[1-9])\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÀ-ÿ\s]{3,55}(?!:))|(?:\b[1-9]\.[1-9]\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]))"
)


@dataclass
class PolicyChunk:
    chunk_id: str
    section: str
    pages: list[int]
    content: str
    embedding: list[float] | None = None


def tokenize_pt(text: str) -> list[str]:
    """Tokeniza texto em português sem acentos e sem stopwords triviais."""
    norm = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]{2,}", norm)
    return [t for t in tokens if t not in PT_STOPWORDS]


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def extract_policy_chunks(pdf_path: Path = POLICY_PDF_PATH) -> list[PolicyChunk]:
    """Extrai o manual em PDF preservando hierarquia de seções entre quebras de página."""
    reader = PdfReader(str(pdf_path))
    cleaned_pages: list[tuple[int, str]] = []

    for idx, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = re.sub(r"\s+", " ", raw).strip()
        text = re.sub(
            r"^Empório da Música Manual de Políticas e Procedimentos\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\s*Página\s+\d+\s*$", "", text, flags=re.IGNORECASE)
        cleaned_pages.append((idx, text))

    chunks: list[PolicyChunk] = []
    if cleaned_pages:
        chunks.append(
            PolicyChunk(
                chunk_id="sec_0_capa",
                section="Capa e Contatos Institucionais",
                pages=[1],
                content=cleaned_pages[0][1],
            )
        )

    # Concatena páginas 2..N com marcadores de página para rastrear origem de cada seção
    combined = ""
    page_spans: list[tuple[int, int, int]] = []
    for page_num, page_text in cleaned_pages[1:]:
        start = len(combined)
        combined += (" " if combined else "") + page_text
        end = len(combined)
        page_spans.append((start, end, page_num))

    # Identifica pontos de corte de seções principais ("1. Título") e subseções ("1.1 Subtítulo")
    heading_regex = re.compile(
        r"\b((?:10|[1-9])\.[1-9]|(?:10|[1-9])\.)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\d•:]{2,55})"
    )
    valid_matches: list[re.Match[str]] = []
    for m in heading_regex.finditer(combined):
        num = m.group(1)
        is_top_section = num.endswith(".")
        if is_top_section:
            matched_top = any(
                combined[m.start() : m.start() + len(title) + 5].startswith(title)
                for title in TOP_SECTION_TITLES
            )
            if not matched_top:
                continue
        valid_matches.append(m)

    current_parent = ""
    for i, match in enumerate(valid_matches):
        start_pos = match.start()
        end_pos = valid_matches[i + 1].start() if i + 1 < len(valid_matches) else len(combined)
        segment = combined[start_pos:end_pos].strip()

        sec_num = match.group(1).rstrip(".")
        is_top_section = match.group(1).endswith(".")
        if is_top_section:
            for top_title in TOP_SECTION_TITLES:
                if segment.startswith(top_title):
                    current_parent = top_title
                    section_label = top_title
                    break
            else:
                current_parent = segment[:60].strip()
                section_label = current_parent
        else:
            # Pega as primeiras palavras do subtítulo da subseção
            sub_match = re.match(
                r"^([1-9]\.[1-9]\s+(?:Direito de Arrependimento \(Compras Online\)|Dados da Empresa|Missão|Regras de Parcelamento|Trocas por Defeito|Trocas por Preferência|Itens Não Elegíveis para Troca|Entregas na Região Metropolitana de Campo Grande|Entregas para Outras Cidades|Código de Rastreamento|Tipos de Promoção|Regras de Promoções|Diretrizes de Atendimento|Fluxo de Atendimento Padrão|Situações Especiais|Garantia Legal|Garantia do Fabricante|O que Não Cobre a Garantia))",
                segment,
            )
            sub_title = sub_match.group(1) if sub_match else f"Seção {sec_num}"
            section_label = f"{current_parent} > {sub_title}" if current_parent else sub_title

        involved_pages = sorted(
            {
                p_num
                for s_idx, e_idx, p_num in page_spans
                if not (end_pos <= s_idx or start_pos >= e_idx)
            }
        )

        # Ignora cabeçalhos vazios que só introduzem subseções sem parágrafo próprio curto
        if len(segment) < 45:
            continue

        chunks.append(
            PolicyChunk(
                chunk_id=f"sec_{sec_num.replace('.', '_')}",
                section=section_label,
                pages=involved_pages or [2],
                content=f"[{section_label}] {segment}",
            )
        )

    return chunks


class PolicyRetriever:
    """Recuperador híbrido (BM25 + Embeddings Gemini com Reciprocal Rank Fusion)."""

    def __init__(
        self,
        pdf_path: Path = POLICY_PDF_PATH,
        cache_path: Path = POLICY_INDEX_CACHE_PATH,
    ) -> None:
        self.pdf_path = pdf_path
        self.cache_path = cache_path
        self.chunks: list[PolicyChunk] = self._load_or_extract_chunks()
        self.tokenized_corpus: list[list[str]] = [
            tokenize_pt(f"{c.section} {c.content}") for c in self.chunks
        ]
        self._avg_dl = (
            sum(len(doc) for doc in self.tokenized_corpus) / len(self.tokenized_corpus)
            if self.tokenized_corpus
            else 1.0
        )
        self._idf = self._compute_idf()

    def _load_or_extract_chunks(self) -> list[PolicyChunk]:
        if self.cache_path.exists():
            try:
                raw_data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                return [PolicyChunk(**item) for item in raw_data["chunks"]]
            except Exception:
                pass
        return extract_policy_chunks(self.pdf_path)

    def build_and_save_embeddings(self, api_key: str | None = None) -> int:
        """Gera embeddings semânticos para os chunks e salva cache JSON versionável."""
        key = (api_key or GEMINI_API_KEY).strip()
        if not key:
            raise ValueError("GEMINI_API_KEY não configurada para gerar embeddings.")

        client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=15000),
        )
        embed_cfg = types.EmbedContentConfig(output_dimensionality=768)
        for chunk in self.chunks:
            resp = client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=chunk.content,
                config=embed_cfg,
            )
            chunk.embedding = [round(v, 6) for v in resp.embeddings[0].values]

        payload = {
            "embedding_model": GEMINI_EMBEDDING_MODEL,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "section": c.section,
                    "pages": c.pages,
                    "content": c.content,
                    "embedding": c.embedding,
                }
                for c in self.chunks
            ],
        }
        self.cache_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return len(self.chunks)

    def _compute_idf(self) -> dict[str, float]:
        n_docs = len(self.tokenized_corpus)
        df: dict[str, int] = {}
        for doc in self.tokenized_corpus:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1
        return {
            term: math.log(1.0 + (n_docs - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def _bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> list[float]:
        q_tokens = tokenize_pt(query)
        scores: list[float] = []
        for doc in self.tokenized_corpus:
            doc_len = len(doc) or 1
            tf_map: dict[str, int] = {}
            for tok in doc:
                tf_map[tok] = tf_map.get(tok, 0) + 1
            score = 0.0
            for qt in q_tokens:
                if qt not in tf_map:
                    continue
                tf = tf_map[qt]
                idf = self._idf.get(qt, 0.0)
                denom = tf + k1 * (1.0 - b + b * (doc_len / self._avg_dl))
                score += idf * ((tf * (k1 + 1.0)) / denom)
            scores.append(score)
        return scores

    def _embed_query(self, query: str) -> list[float] | None:
        if not GEMINI_API_KEY or not any(c.embedding for c in self.chunks):
            return None
        try:
            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=6000),
            )
            resp = client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=query,
                config=types.EmbedContentConfig(output_dimensionality=768),
            )
            return list(resp.embeddings[0].values)
        except Exception:
            return None

    def search(
        self, query: str, top_k: int = 4, use_semantic: bool = True
    ) -> list[dict[str, Any]]:
        """Busca trechos relevantes combinando ranking semântico e léxico via RRF."""
        bm25 = self._bm25_scores(query)
        bm25_ranked = sorted(
            range(len(self.chunks)), key=lambda i: bm25[i], reverse=True
        )

        rrf_scores = {i: 0.0 for i in range(len(self.chunks))}
        rrf_k = 20.0
        for rank, idx in enumerate(bm25_ranked):
            if bm25[idx] > 0:
                rrf_scores[idx] += 1.0 / (rrf_k + rank + 1)

        query_vec = self._embed_query(query) if use_semantic else None
        mode = "hybrid_rrf" if query_vec else "bm25_lexical"

        if query_vec:
            sem_sims = [
                _cosine_similarity(query_vec, c.embedding) if c.embedding else 0.0
                for c in self.chunks
            ]
            sem_ranked = sorted(
                range(len(self.chunks)), key=lambda i: sem_sims[i], reverse=True
            )
            for rank, idx in enumerate(sem_ranked):
                # Peso levemente maior para similaridade semântica
                rrf_scores[idx] += 1.35 / (rrf_k + rank + 1)

        best_indices = sorted(
            range(len(self.chunks)), key=lambda i: rrf_scores[i], reverse=True
        )[:top_k]

        results: list[dict[str, Any]] = []
        for idx in best_indices:
            chunk = self.chunks[idx]
            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "section": chunk.section,
                    "pages": chunk.pages,
                    "retrieval_mode": mode,
                    "score": round(rrf_scores[idx], 4),
                    "content": chunk.content,
                }
            )
        return results


_retriever_instance: PolicyRetriever | None = None


def get_policy_retriever() -> PolicyRetriever:
    """Retorna instância singleton do índice RAG de políticas."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = PolicyRetriever()
    return _retriever_instance
