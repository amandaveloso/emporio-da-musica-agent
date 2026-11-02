"""API FastAPI da Empório da Música (compatível com execução local e Vercel Serverless)."""

from __future__ import annotations

import os
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

app = FastAPI(
    title="Empório da Música — Assistente Virtual API",
    description="Agente híbrido (Function Calling + SQLite + RAG) para atendimento ao cliente.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limit simples em memória por IP para proteger a chave gratuita em ambiente público
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_REQ = 15
_ip_requests: dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    q = _ip_requests[client_ip]
    while q and (now - q[0]) > RATE_LIMIT_WINDOW_SEC:
        q.popleft()
    if len(q) >= RATE_LIMIT_MAX_REQ:
        raise HTTPException(
            status_code=429,
            detail="Muitas mensagens enviadas em sequência. Aguarde alguns segundos e tente novamente.",
        )
    q.append(now)


def _store_open_status_ms() -> dict[str, Any]:
    """Calcula se a loja física em Campo Grande/MS (UTC-4) está aberta agora (Seção 2 do Manual)."""
    tz_ms = timezone(timedelta(hours=-4))
    now_ms = datetime.now(tz_ms)
    weekday = now_ms.weekday()  # 0=Seg .. 5=Sáb, 6=Dom
    minutes = now_ms.hour * 60 + now_ms.minute

    is_open = False
    if 0 <= weekday <= 4 and (9 * 60) <= minutes < (18 * 60):
        is_open = True
    elif weekday == 5 and (9 * 60) <= minutes < (13 * 60):
        is_open = True

    return {
        "timezone": "America/Campo_Grande (UTC-4)",
        "local_time": now_ms.strftime("%H:%M"),
        "is_open_now": is_open,
        "schedule_label": "Seg–Sex 09h às 18h • Sáb 09h às 13h",
    }


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)
    session_id: str = Field(default="web-default", min_length=1, max_length=80)
    history: list[HistoryItem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model_used: str
    tool_traces: list[dict[str, Any]]
    latency_ms: int


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    from src.database import get_catalog_db

    db_summary = get_catalog_db().audit_summary()
    return {
        "status": "ok",
        "store": "Empório da Música — Campo Grande/MS",
        "store_hours": _store_open_status_ms(),
        "catalog": db_summary,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, request: Request) -> ChatResponse:
    from src.agent import get_agent

    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "local")
    )
    _check_rate_limit(client_ip)

    try:
        agent = get_agent()
        fallback_hist = [h.model_dump() for h in payload.history]
        result = agent.chat(
            user_message=payload.message,
            session_id=payload.session_id,
            fallback_history=fallback_hist,
        )
        return ChatResponse(
            reply=result.reply,
            session_id=result.session_id,
            model_used=result.model_used,
            tool_traces=result.tool_traces,
            latency_ms=result.latency_ms,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Serviço de IA temporariamente indisponível: {exc}",
        ) from exc


@app.get("/api/session/{session_id}")
def get_session_history(session_id: str) -> dict[str, Any]:
    from src.agent import get_agent

    agent = get_agent()
    return {
        "session_id": session_id,
        "messages": agent.memory.get_history(session_id, limit=30),
    }


@app.delete("/api/session/{session_id}")
def reset_session(session_id: str) -> dict[str, str]:
    from src.agent import get_agent

    agent = get_agent()
    agent.memory.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


IS_SERVERLESS = bool(
    os.getenv("VERCEL")
    or os.getenv("VERCEL_ENV")
    or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
)
PUBLIC_DIR = ROOT_DIR / "public"
if not IS_SERVERLESS and PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
