"""Testes automatizados de regras de negócio, higienização de dados, RAG, LGPD e API."""

from __future__ import annotations

from pathlib import Path

from api.index import PUBLIC_DIR, app, health_check
from src.database import get_catalog_db
from src.memory import ConversationMemory
from src.rag import get_policy_retriever
from src.tools import (
    buscar_catalogo_instrumentos,
    calcular_condicoes_pagamento,
    consultar_pedido_cliente,
    listar_categorias_e_promocoes_ativas,
)


def test_database_audit_and_anomalies() -> None:
    summary = get_catalog_db().audit_summary()
    assert summary["total_products"] == 65
    assert summary["available_products"] == 61
    assert summary["active_promotions"] == 4
    assert summary["expired_promotions"] == 21
    assert summary["flagged_products_with_anomalies"] >= 7
    assert "Instrumentos de Sopro (Madeiras)" in summary["empty_categories"]


def test_expired_promotion_is_not_applied_takamine_gd20() -> None:
    res = buscar_catalogo_instrumentos(termo_busca="Takamine GD20")
    assert res["total_encontrados"] == 1
    gd20 = res["produtos"][0]
    pagamento = gd20["condicoes_pagamento"]

    assert pagamento["preco_tabela_brl"] == 2199.0
    assert pagamento["em_promocao_ativa"] is False
    assert pagamento["preco_vigente_brl"] == 2199.0
    assert pagamento["preco_pix_avista_brl"] == 2089.05  # 5% PIX
    assert pagamento["parcelamento_cartao_sem_juros"]["max_parcelas"] == 12
    assert len(gd20["promocoes_expiradas_historico"]) == 1


def test_active_promotion_is_not_cumulative_with_pix() -> None:
    res = buscar_catalogo_instrumentos(termo_busca="Crafter HT-100")
    ht100 = res["produtos"][0]
    pagamento = ht100["condicoes_pagamento"]

    assert pagamento["em_promocao_ativa"] is True
    assert pagamento["promocao_ativa"]["desconto_percentual"] == 18.0
    assert pagamento["preco_vigente_brl"] == 1967.18
    # Não cumulativo com os 5% do PIX (Seção 6.2)
    assert pagamento["preco_pix_avista_brl"] == 1967.18


def test_installment_tiers_section_3_1() -> None:
    # R$ 80,00 -> abaixo de 2x de R$ 50, então 1x
    p_80 = calcular_condicoes_pagamento(80.0)
    assert p_80["parcelamento_cartao_sem_juros"]["max_parcelas"] == 1

    # R$ 159,90 (Shelby SU-21S) -> 3x de R$ 53,30 (>= 50), mas 4x daria 39,97 (< 80)
    p_159 = calcular_condicoes_pagamento(159.9)
    assert p_159["parcelamento_cartao_sem_juros"]["max_parcelas"] == 3

    # R$ 480,00 -> 6x de R$ 80,00 (>= 80), mas 7x daria 68,57 (< 100)
    p_480 = calcular_condicoes_pagamento(480.0)
    assert p_480["parcelamento_cartao_sem_juros"]["max_parcelas"] == 6

    # R$ 1200,00 -> 12x de R$ 100,00
    p_1200 = calcular_condicoes_pagamento(1200.0)
    assert p_1200["parcelamento_cartao_sem_juros"]["max_parcelas"] == 12


def test_catalog_filter_violoes_under_1000_excludes_out_of_stock_and_discontinued() -> None:
    res = buscar_catalogo_instrumentos(categoria="Violões", preco_max=1000.0)
    assert res["total_encontrados"] == 12
    for prod in res["produtos"]:
        assert prod["disponibilidade"] == "disponivel_em_estoque"
        assert prod["condicoes_pagamento"]["preco_vigente_brl"] <= 1000.0


def test_discontinued_and_out_of_stock_suggest_alternatives() -> None:
    # Ibanez Bass 2X tem stock=13 no CSV, porém status=discontinued
    ibz = buscar_catalogo_instrumentos(termo_busca="Ibanez Bass 2X")
    assert ibz["produtos"][0]["disponibilidade"] == "descontinuado"
    assert ibz["produtos"][0]["quantidade_estoque"] == 0
    assert len(ibz["alternativas_disponiveis_sugeridas"]) >= 1

    # Giannini GF-3D tem status=active, porém stock=0
    gf3d = buscar_catalogo_instrumentos(termo_busca="Giannini GF-3D")
    assert gf3d["produtos"][0]["disponibilidade"] == "temporariamente_sem_estoque"
    assert len(gf3d["alternativas_disponiveis_sugeridas"]) >= 1


def test_standalone_accessories_trigger_scope_alert() -> None:
    res = buscar_catalogo_instrumentos(termo_busca="palhetas e encordoamento")
    assert res["total_encontrados"] == 0
    assert "alerta_escopo_acessorios" in res


def test_order_lookup_enforces_lgpd_verification() -> None:
    unverified = consultar_pedido_cliente(8)
    assert unverified["encontrado"] is True
    assert unverified["verificado_lgpd"] is False
    assert "codigo_rastreamento" not in unverified

    verified = consultar_pedido_cliente(8, confirmacao_cliente="Ana Carolina")
    assert verified["verificado_lgpd"] is True
    assert verified["codigo_rastreamento"] == "BRJL5544332BR"
    assert verified["status_sistema"] == "shipped"


def test_rag_policy_retrieval_sections() -> None:
    retriever = get_policy_retriever()
    assert len(retriever.chunks) >= 20

    hits_arrep = retriever.search("arrependimento devolver compra online 7 dias", top_k=2, use_semantic=False)
    assert any("4.1" in h["section"] for h in hits_arrep)

    hits_frete = retriever.search("frete gratis motoboy Campo Grande", top_k=2, use_semantic=False)
    assert any("5.1" in h["section"] for h in hits_frete)


def test_conversation_memory_lifecycle(tmp_path: Path) -> None:
    mem = ConversationMemory(db_path=tmp_path / "test_sessions.db")
    mem.add_message("s1", "user", "Oi")
    mem.add_message("s1", "model", "Olá!", model_used="gemini-3.5-flash")
    hist = mem.get_history("s1")
    assert len(hist) == 2
    assert hist[0]["content"] == "Oi"
    mem.clear_session("s1")
    assert mem.get_history("s1") == []


def test_fastapi_health_and_ui_serving() -> None:
    health = health_check()
    assert health["status"] == "ok"
    assert health["catalog"]["total_products"] == 65

    route_paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/health" in route_paths
    assert "/api/chat" in route_paths

    index_html = (PUBLIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "Empório da Música" in index_html

    promos = listar_categorias_e_promocoes_ativas()
    assert len(promos["promocoes_ativas_hoje"]) == 4
