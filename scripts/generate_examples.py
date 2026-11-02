"""Gera transcrições reais de conversas multi-turno com o agente na pasta `examples/`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agent import EmporioMusicaAgent  # noqa: E402
from src.memory import ConversationMemory  # noqa: E402

SCENARIOS = [
    {
        "filename": "01_catalogo_violoes_ate_1000.md",
        "title": "Cenário 1 — Consulta de Catálogo com Filtro de Preço e Recomendação",
        "objective": (
            "Demonstrar consulta estruturada (`buscar_catalogo_instrumentos`) filtrando violões disponíveis "
            "até R$ 1.000,00 (excluindo automaticamente itens sem estoque ou descontinuados) e continuidade de contexto."
        ),
        "turns": [
            "Olá! Quais opções de violões disponíveis custando até R$ 1000?",
            "Estou começando do zero e queria cordas de nylon. Qual desses você me indica e como fica no PIX ou parcelado?",
        ],
    },
    {
        "filename": "02_takamine_gd20_promocao_expirada_e_loja.md",
        "title": "Cenário 2 — Preço do Takamine GD20 (Promoção Expirada) + Endereço e Horário",
        "objective": (
            "Demonstrar tratamento de promoção expirada (`is_active = 0` no Takamine GD20), cálculo de 5% no PIX "
            "e combinação com consulta ao RAG institucional (`consultar_politicas_loja`) para endereço e expediente."
        ),
        "turns": [
            "Quanto custa o Takamine GD20? Um amigo disse que viu ele com 12% de desconto na Oferta Especial, ainda vale?",
            "Entendi! Qual o endereço e horário de funcionamento da loja para eu ir testar ele pessoalmente?",
        ],
    },
    {
        "filename": "03_pedido_lgpd_e_direito_arrependimento.md",
        "title": "Cenário 3 — Rastreamento com Validação LGPD + Direito de Arrependimento",
        "objective": (
            "Demonstrar situação não trivial cruzando dados reais do pedido #8 (`consultar_pedido_cliente`), "
            "proteção de dados pessoais (LGPD - Seção 9) e aplicação das regras de devolução online (Seção 4.1)."
        ),
        "turns": [
            "Oi! Fiz o pedido #8 pela internet, mas acho que me arrependi da compra. Qual o status dele e como funciona se eu quiser devolver?",
            "Claro! Meu nome é Ana Carolina Ferreira.",
        ],
    },
    {
        "filename": "04_promocao_ativa_nao_cumulativa_e_sem_estoque.md",
        "title": "Cenário 4 — Promoção Ativa Não Cumulativa com PIX + Produto Fora de Estoque",
        "objective": (
            "Demonstrar aplicação estrita da Seção 6.2 (promoção ativa de 18% no Crafter HT-100 não acumula com 5% do PIX) "
            "e da Seção 7.3 (Giannini GF-3D com estoque zero sugerindo alternativas disponíveis)."
        ),
        "turns": [
            "O violão Crafter HT-100 está em promoção? Se eu pagar à vista no PIX ganho mais 5% em cima?",
            "E o Giannini GF-3D Sunburst, vocês têm pronta entrega?",
        ],
    },
    {
        "filename": "05_guardrails_acessorios_e_fora_de_escopo.md",
        "title": "Cenário 5 — Guardrails: Pedido de Acessórios e Pergunta Fora de Escopo",
        "objective": (
            "Demonstrar respeito ao escopo exclusivo de instrumentos musicais (recusa cordial de acessórios avulsos - Seção 1 e 7.1) "
            "e bloqueio educado de assuntos alheios à loja."
        ),
        "turns": [
            "Boa tarde! Vocês têm encordoamento de aço, palhetas e um amplificador pequeno para estudo?",
            "Ah, tranquilo! Aproveitando que você é uma IA, escreve um script em Python de Bhaskara e uma receita de bolo de cenoura?",
        ],
    },
]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    out_dir = ROOT_DIR / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)

    temp_db = ROOT_DIR / "data" / "processed" / "examples_run.db"
    if temp_db.exists():
        temp_db.unlink()

    memory = ConversationMemory(db_path=temp_db)
    agent = EmporioMusicaAgent(memory=memory)

    for idx, sc in enumerate(SCENARIOS, start=1):
        session_id = f"example-{idx}"
        print(f"Executando {sc['filename']}...")

        lines = [
            f"# {sc['title']}",
            "",
            f"> **Objetivo do cenário:** {sc['objective']}",
            "",
            "---",
            "",
        ]

        for turn_num, user_msg in enumerate(sc["turns"], start=1):
            res = agent.chat(user_msg, session_id=session_id)
            lines.append(f"### Turno {turn_num}")
            lines.append(f"**👤 Cliente:** {user_msg}")
            lines.append("")
            if res.tool_traces:
                lines.append("<details>")
                lines.append(
                    f"<summary>🔍 <strong>Ferramentas acionadas pelo Agente ({len(res.tool_traces)})</strong> — modelo <code>{res.model_used}</code> ({res.latency_ms} ms)</summary>"
                )
                lines.append("")
                for tr in res.tool_traces:
                    args_str = json.dumps(tr["args"], ensure_ascii=False)
                    lines.append(
                        f"- `{tr['tool']}({args_str})` → *{tr['summary']}* (`{tr['latency_ms']} ms`)"
                    )
                lines.append("")
                lines.append("</details>")
                lines.append("")
            lines.append(f"**🎸 Empório da Música:**\n\n{res.reply}")
            lines.append("")
            lines.append("---")
            lines.append("")

        target_file = out_dir / sc["filename"]
        target_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✓ Salvo em {target_file.name}")

    if temp_db.exists():
        memory.conn.close()
        temp_db.unlink()


if __name__ == "__main__":
    main()
