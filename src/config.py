"""Configurações centrais do projeto Empório da Música."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Carrega variáveis do arquivo .env local, se existir
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

# Lista ordenada de modelos para fallback automático em caso de pico (HTTP 503/429)
MODEL_FALLBACK_CHAIN: list[str] = [
    GEMINI_MODEL,
    os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip(),
    "gemini-3.8-flash",
]
# Remove duplicatas mantendo a ordem
MODEL_FALLBACK_CHAIN = list(dict.fromkeys(m for m in MODEL_FALLBACK_CHAIN if m))

GEMINI_EMBEDDING_MODEL: str = os.getenv(
    "GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"
).strip()

IS_VERCEL: bool = bool(os.getenv("VERCEL"))

# Caminho de persistência do histórico de sessões (local vs serverless /tmp)
if IS_VERCEL:
    SESSIONS_DB_PATH = Path("/tmp/emporio_sessions.db")
else:
    PROCESSED_DIR = DATA_DIR / "processed"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DB_PATH = PROCESSED_DIR / "sessions.db"

POLICY_INDEX_CACHE_PATH = DATA_DIR / "policies_index.json"
POLICY_PDF_PATH = DATA_DIR / "políticas_da_loja.pdf"
