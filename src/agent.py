"""Orquestrador do Agente Híbrido (Function Calling + SQLite + RAG) com Fallback."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from google import genai
from google.genai import errors, types

from src.config import GEMINI_API_KEY, MODEL_FALLBACK_CHAIN
from src.memory import ConversationMemory, get_memory
from src.prompts import SYSTEM_PROMPT
from src.tools import AGENT_TOOLS

TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    fn.__name__: fn for fn in AGENT_TOOLS
}


@dataclass
class AgentTurnResult:
    reply: str
    session_id: str
    model_used: str
    tool_traces: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0


def _summarize_tool_output(tool_name: str, result: dict[str, Any]) -> str:
    """Cria um resumo legível da resposta da tool para o painel de inspeção na interface."""
    if tool_name == "buscar_catalogo_instrumentos":
        total = result.get("total_encontrados", 0)
        names = [p["nome"] for p in result.get("produtos", [])[:3]]
        sample = ", ".join(names) + ("..." if total > 3 else "")
        return f"{total} instrumento(s) retornado(s)" + (f": {sample}" if sample else "")
    if tool_name == "listar_categorias_e_promocoes_ativas":
        cats = len(result.get("categorias", []))
        promos = len(result.get("promocoes_ativas_hoje", []))
        return f"{cats} categorias e {promos} promoções ativas listadas"
    if tool_name == "consultar_pedido_cliente":
        if not result.get("encontrado"):
            return f"Pedido #{result.get('order_id')} não encontrado"
        if not result.get("verificado_lgpd"):
            return f"Pedido #{result.get('order_id')} localizado — aguardando confirmação LGPD"
        return f"Pedido #{result.get('order_id')} validado ({result.get('status_legivel')})"
    if tool_name == "consultar_politicas_loja":
        secs = [t["section"] for t in result.get("trechos_manual", [])[:2]]
        return "Seções recuperadas: " + " | ".join(secs)
    return "Consulta concluída"


class EmporioMusicaAgent:
    """Agente conversacional de atendimento ao cliente da Empório da Música."""

    def __init__(
        self,
        api_key: str | None = None,
        memory: ConversationMemory | None = None,
        models: list[str] | None = None,
    ) -> None:
        self.api_key = (api_key or GEMINI_API_KEY).strip()
        self.memory = memory or get_memory()
        self.models = models or MODEL_FALLBACK_CHAIN
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Defina no arquivo .env ou nas variáveis de ambiente."
            )
        if self._client is None:
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=20000,
                    retry_options=types.HttpRetryOptions(
                        attempts=2,
                        initial_delay=0.5,
                        max_delay=1.5,
                    ),
                ),
            )
        return self._client

    def _build_contents(
        self,
        session_id: str,
        user_message: str,
        fallback_history: list[dict[str, str]] | None = None,
    ) -> list[types.Content]:
        stored = self.memory.get_history(session_id, limit=14)
        # Se a instância serverless reiniciou e o banco /tmp estiver vazio, sincroniza do cliente
        if not stored and fallback_history:
            for item in fallback_history[-10:]:
                role = item.get("role", "user")
                text = (item.get("content") or "").strip()
                if role in {"user", "assistant", "model"} and text:
                    norm_role = "user" if role == "user" else "model"
                    self.memory.add_message(session_id, norm_role, text)
            stored = self.memory.get_history(session_id, limit=14)

        contents: list[types.Content] = []
        for turn in stored:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=turn["content"])],
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)],
            )
        )
        return contents

    def _generate_with_fallback(
        self, contents: list[types.Content], config: types.GenerateContentConfig
    ) -> tuple[types.GenerateContentResponse, str]:
        last_err: Exception | None = None
        for model_name in self.models:
            try:
                resp = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                return resp, model_name
            except (errors.ServerError, errors.ClientError) as exc:
                last_err = exc
                status_code = getattr(exc, "code", None)
                # Faz fallback imediato em indisponibilidade (503), rate limit (429) ou modelo descontinuado (404)
                if status_code in {404, 429, 500, 502, 503, 504}:
                    continue
                raise
        raise RuntimeError(
            f"Todos os modelos da cadeia falharam temporariamente. Último erro: {last_err}"
        )

    def chat(
        self,
        user_message: str,
        session_id: str = "default",
        fallback_history: list[dict[str, str]] | None = None,
        max_tool_rounds: int = 5,
    ) -> AgentTurnResult:
        clean_msg = user_message.strip()
        if not clean_msg:
            return AgentTurnResult(
                reply="Olá! Como posso ajudar você hoje aqui na Empório da Música?",
                session_id=session_id,
                model_used="none",
            )

        t0 = time.perf_counter()
        contents = self._build_contents(session_id, clean_msg, fallback_history)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=AGENT_TOOLS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
            thinking_config=types.ThinkingConfig(thinking_budget=256),
            temperature=0.25,
        )

        tool_traces: list[dict[str, Any]] = []
        model_used = self.models[0]
        final_text = ""

        for _ in range(max_tool_rounds):
            response, model_used = self._generate_with_fallback(contents, config)
            candidate = response.candidates[0]
            model_content = candidate.content
            function_calls = response.function_calls or []

            if not function_calls:
                final_text = (response.text or "").strip()
                break

            # Preserva o Content completo do modelo (incluindo eventuais thought signatures)
            contents.append(model_content)

            fn_response_parts: list[types.Part] = []
            for fc in function_calls:
                fn_name = fc.name
                fn_args = dict(fc.args or {})
                tool_t0 = time.perf_counter()

                tool_fn = TOOL_REGISTRY.get(fn_name)
                if tool_fn is None:
                    tool_output = {"erro": f"Ferramenta '{fn_name}' desconhecida."}
                else:
                    try:
                        tool_output = tool_fn(**fn_args)
                    except Exception as exc:
                        tool_output = {"erro": f"Falha ao executar {fn_name}: {exc}"}

                tool_ms = int((time.perf_counter() - tool_t0) * 1000)
                tool_traces.append(
                    {
                        "tool": fn_name,
                        "args": fn_args,
                        "summary": _summarize_tool_output(fn_name, tool_output),
                        "latency_ms": tool_ms,
                    }
                )
                fn_response_parts.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": tool_output},
                    )
                )

            contents.append(types.Content(role="user", parts=fn_response_parts))
        else:
            # Caso atinja o limite de rodadas de ferramentas, gera síntese final sem novas tools
            final_cfg = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.25,
            )
            response, model_used = self._generate_with_fallback(contents, final_cfg)
            final_text = (response.text or "").strip()

        if not final_text:
            final_text = (
                "Desculpe, tive uma instabilidade momentânea ao consultar nosso sistema. "
                "Pode repetir sua pergunta?"
            )

        # Persiste turno do usuário e resposta do agente
        self.memory.add_message(session_id, "user", clean_msg)
        self.memory.add_message(
            session_id,
            "model",
            final_text,
            tool_traces=tool_traces,
            model_used=model_used,
        )

        total_ms = int((time.perf_counter() - t0) * 1000)
        return AgentTurnResult(
            reply=final_text,
            session_id=session_id,
            model_used=model_used,
            tool_traces=tool_traces,
            latency_ms=total_ms,
        )


_agent_instance: EmporioMusicaAgent | None = None


def get_agent() -> EmporioMusicaAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = EmporioMusicaAgent()
    return _agent_instance
