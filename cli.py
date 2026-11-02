"""Interface de linha de comando (CLI) interativa para testar o agente localmente."""

from __future__ import annotations

import sys
import uuid

from src.agent import get_agent


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    session_id = f"cli-{uuid.uuid4().hex[:8]}"
    agent = get_agent()

    print("=" * 68)
    print("🎸 EMPÓRIO DA MÚSICA — Assistente Virtual (Modo Terminal / CLI)")
    print("   Sua música começa aqui. | Campo Grande - MS")
    print("   Comandos: '/limpar' para nova conversa | '/sair' para encerrar")
    print("=" * 68)

    while True:
        try:
            user_input = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo! 🎶")
            break

        if not user_input:
            continue
        if user_input.lower() in {"/sair", "sair", "exit", "quit"}:
            print("\nEmpório da Música: Valeu pelo papo! Precisando, estamos à disposição. 🎶")
            break
        if user_input.lower() in {"/limpar", "limpar", "/reset"}:
            agent.memory.clear_session(session_id)
            print("✨ Histórico da conversa reiniciado.")
            continue

        try:
            result = agent.chat(user_input, session_id=session_id)
            if result.tool_traces:
                print("\n  [Raio-X Tools]:")
                for trace in result.tool_traces:
                    print(
                        f"   • {trace['tool']}({trace['args']}) -> {trace['summary']} ({trace['latency_ms']}ms)"
                    )
            print(f"\nEmpório da Música ({result.model_used}):\n{result.reply}")
        except Exception as exc:
            print(f"\n[Erro]: {exc}")


if __name__ == "__main__":
    main()
