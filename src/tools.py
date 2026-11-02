"""Ferramentas determinísticas (Tools) para consulta de catálogo, pedidos e políticas."""

from __future__ import annotations

import json
import re
from typing import Any

from src.database import get_catalog_db, normalize_text
from src.rag import get_policy_retriever

STANDALONE_ACCESSORIES = {
    "encordoamento",
    "palheta",
    "palhetas",
    "cabo",
    "cabos",
    "case",
    "cases",
    "bag",
    "capa",
    "pedal",
    "pedais",
    "pedaleira",
    "amplificador",
    "amplificadores",
    "cubo",
    "correia",
    "suporte",
    "estante",
    "capotraste",
    "baqueta",
    "baquetas",
}


def calcular_condicoes_pagamento(
    price_brl: float,
    active_promo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calcula preços à vista, PIX e parcelamento seguindo as Seções 3, 3.1 e 6.2 do Manual."""
    original_price = round(float(price_brl), 2)

    if active_promo:
        discount_pct = float(active_promo["discount_percent"])
        effective_price = round(original_price * (1.0 - discount_pct / 100.0), 2)
        pix_price = effective_price
        pix_note = (
            "Produto já possui promoção ativa; conforme Seção 6.2 do Manual, "
            "promoções não são cumulativas com o desconto de 5% do PIX."
        )
    else:
        discount_pct = 0.0
        effective_price = original_price
        pix_price = round(original_price * 0.95, 2)
        pix_note = "5% de desconto para pagamento à vista no PIX (sobre preço fora de promoção)."

    # Regras de parcelamento sem juros (Seção 3.1):
    # - 7x a 12x: parcela mínima R$ 100,00
    # - 4x a 6x: parcela mínima R$ 80,00
    # - até 3x: parcela mínima R$ 50,00
    max_installments = 1
    for n in range(12, 1, -1):
        installment_val = effective_price / n
        if 7 <= n <= 12 and installment_val >= 100.0 - 1e-9:
            max_installments = n
            break
        if 4 <= n <= 6 and installment_val >= 80.0 - 1e-9:
            max_installments = n
            break
        if 2 <= n <= 3 and installment_val >= 50.0 - 1e-9:
            max_installments = n
            break

    installment_value = round(effective_price / max_installments, 2)
    allows_split_payment = effective_price > 2000.0

    return {
        "preco_tabela_brl": original_price,
        "em_promocao_ativa": bool(active_promo),
        "promocao_ativa": (
            {
                "campanha": active_promo["description"],
                "desconto_percentual": discount_pct,
                "preco_promocional_brl": effective_price,
            }
            if active_promo
            else None
        ),
        "preco_vigente_brl": effective_price,
        "preco_pix_avista_brl": pix_price,
        "regra_pix": pix_note,
        "parcelamento_cartao_sem_juros": {
            "max_parcelas": max_installments,
            "valor_parcela_brl": installment_value,
            "resumo": (
                f"Até {max_installments}x de R$ {installment_value:.2f} sem juros no cartão de crédito"
                if max_installments > 1
                else "Pagamento em 1x no cartão (parcela mínima para 2x é R$ 50,00)"
            ),
        },
        "permite_combinar_pagamentos": allows_split_payment,
    }


def _enrich_product_row(conn: Any, row: Any) -> dict[str, Any]:
    product_id = row["product_id"]
    promos = conn.execute(
        """
        SELECT promotion_id, discount_percent, description, is_active
        FROM promotions
        WHERE product_id = ?
        ORDER BY is_active DESC, discount_percent DESC
        """,
        (product_id,),
    ).fetchall()

    active_promo = next((dict(p) for p in promos if p["is_active"] == 1), None)
    expired_promos = [
        {
            "campanha": p["description"],
            "desconto_percentual": p["discount_percent"],
            "status": "expirada",
        }
        for p in promos
        if p["is_active"] == 0
    ]

    pricing = calcular_condicoes_pagamento(row["price_brl"], active_promo)

    status = row["status"]
    stock = row["stock_quantity"]
    if status == "discontinued":
        disponibilidade = "descontinuado"
    elif status == "coming_soon":
        disponibilidade = "em_breve_pre_lancamento"
    elif status == "active" and stock > 0:
        disponibilidade = "disponivel_em_estoque"
    else:
        disponibilidade = "temporariamente_sem_estoque"

    return {
        "product_id": product_id,
        "nome": row["name"],
        "categoria": row["category_name"],
        "disponibilidade": disponibilidade,
        "status_sistema": status,
        "quantidade_estoque": stock if status == "active" else 0,
        "descricao": row["description"],
        "especificacoes": json.loads(row["specs_json"] or "{}"),
        "condicoes_pagamento": pricing,
        "promocoes_expiradas_historico": expired_promos,
        "observacoes_auditoria_cadastro": row["data_quality_notes"],
    }


def buscar_catalogo_instrumentos(
    termo_busca: str = "",
    categoria: str = "",
    preco_max: float | None = None,
    preco_min: float | None = None,
    incluir_indisponiveis: bool = False,
) -> dict[str, Any]:
    """Busca instrumentos musicais no catálogo da loja filtrando por termo, categoria e faixa de preço.

    Use sempre esta ferramenta para responder sobre disponibilidade, estoque, modelos, preços,
    descontos promocionais, valor no PIX e parcelamento de instrumentos.
    """
    db = get_catalog_db()
    conn = db.conn

    norm_query = normalize_text(termo_busca)
    norm_cat = normalize_text(categoria)

    # Verifica se o cliente está buscando acessórios avulsos (fora do escopo da loja)
    query_words = set(re.findall(r"[a-z0-9]+", norm_query))
    accessory_hits = sorted(query_words.intersection(STANDALONE_ACCESSORIES))

    sql = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        WHERE 1=1
    """
    params: list[Any] = []

    if norm_cat:
        # Trata singular/plural comum em português (ex.: violões -> violao/violoes)
        cat_stem = re.sub(r"(oes|ais|is|s)$", "", norm_cat)
        sql += " AND (NORM(c.name) LIKE ? OR NORM(c.description) LIKE ?)"
        params.extend([f"%{cat_stem}%", f"%{cat_stem}%"])

    if norm_query:
        tokens = [
            re.sub(r"(oes|aes|ais|ns|s)$", "", t)
            for t in re.findall(r"[a-z0-9-]+", norm_query)
            if len(t) >= 2 and t not in {"de", "da", "do", "com", "para", "ate", "em"}
        ]
        for tok in tokens:
            if not tok:
                continue
            sql += """
                AND (
                    NORM(p.name) LIKE ?
                    OR NORM(p.description) LIKE ?
                    OR NORM(c.name) LIKE ?
                    OR NORM(p.specs_json) LIKE ?
                )
            """
            like_val = f"%{tok}%"
            params.extend([like_val, like_val, like_val, like_val])

    rows = conn.execute(sql + " ORDER BY p.price_brl ASC", params).fetchall()
    enriched = [_enrich_product_row(conn, r) for r in rows]

    # Filtro de faixa de preço usando o preço vigente (considerando promoção ativa, se houver)
    if preco_min is not None:
        enriched = [
            item
            for item in enriched
            if item["condicoes_pagamento"]["preco_vigente_brl"] >= float(preco_min)
        ]
    if preco_max is not None:
        enriched = [
            item
            for item in enriched
            if item["condicoes_pagamento"]["preco_vigente_brl"] <= float(preco_max)
        ]

    available_items = [
        i for i in enriched if i["disponibilidade"] == "disponivel_em_estoque"
    ]
    unavailable_items = [
        i for i in enriched if i["disponibilidade"] != "disponivel_em_estoque"
    ]

    # Se o cliente buscou um modelo específico que está sem estoque ou descontinuado,
    # retornamos o status real + alternativas disponíveis da mesma categoria (Seção 7.3)
    alternatives: list[dict[str, Any]] = []
    if not available_items and unavailable_items:
        target = unavailable_items[0]
        target_cat = normalize_text(target["categoria"])
        target_price = target["condicoes_pagamento"]["preco_vigente_brl"]
        alt_rows = conn.execute(
            """
            SELECT p.*, c.name AS category_name
            FROM products p
            JOIN categories c ON c.category_id = p.category_id
            WHERE NORM(c.name) = ? AND p.status = 'active' AND p.stock_quantity > 0
            ORDER BY ABS(p.price_brl - ?) ASC
            LIMIT 3
            """,
            (target_cat, target_price),
        ).fetchall()
        alternatives = [_enrich_product_row(conn, r) for r in alt_rows]

    result_items = (
        enriched if (incluir_indisponiveis or not available_items) else available_items
    )

    response: dict[str, Any] = {
        "total_encontrados": len(result_items),
        "produtos": result_items[:12],
    }
    if len(result_items) > 12:
        response["aviso_paginacao"] = (
            f"Exibindo os 12 primeiros de {len(result_items)} instrumentos encontrados (ordenados do menor para o maior preço)."
        )
    if alternatives:
        response["alternativas_disponiveis_sugeridas"] = alternatives
    if accessory_hits and not result_items:
        response["alerta_escopo_acessorios"] = (
            f"Termo contém acessório(s) ({', '.join(accessory_hits)}). "
            "Lembrete da Seção 1 e 7.1 do Manual: a Empório da Música trabalha EXCLUSIVAMENTE com "
            "instrumentos musicais e não comercializa acessórios avulsos (cordas, palhetas, cabos, cases, pedais ou amplificadores)."
        )
    return response


def listar_categorias_e_promocoes_ativas() -> dict[str, Any]:
    """Lista todas as categorias da loja (com contagem de itens disponíveis) e todas as promoções ativas no momento."""
    db = get_catalog_db()
    conn = db.conn

    cat_rows = conn.execute(
        """
        SELECT
            c.category_id,
            c.name,
            c.description,
            SUM(CASE WHEN p.status = 'active' AND p.stock_quantity > 0 THEN 1 ELSE 0 END) AS disponiveis
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.category_id
        GROUP BY c.category_id
        ORDER BY c.category_id
        """
    ).fetchall()

    promo_rows = conn.execute(
        """
        SELECT p.*, c.name AS category_name
        FROM promotions pr
        JOIN products p ON p.product_id = pr.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE pr.is_active = 1
        ORDER BY pr.discount_percent DESC
        """
    ).fetchall()

    return {
        "categorias": [dict(r) for r in cat_rows],
        "promocoes_ativas_hoje": [_enrich_product_row(conn, r) for r in promo_rows],
    }


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    user, domain = email.split("@", 1)
    prefix = user[:2] if len(user) >= 2 else user[:1]
    return f"{prefix}***@{domain}"


def consultar_pedido_cliente(
    order_id: int, confirmacao_cliente: str = ""
) -> dict[str, Any]:
    """Consulta status, itens, rastreamento e histórico de um pedido pelo número (order_id).

    Por conformidade com a LGPD (Seção 9 do Manual), exige confirmação de nome, e-mail ou
    telefone do titular em `confirmacao_cliente` antes de liberar dados pessoais e detalhes do pedido.
    """
    db = get_catalog_db()
    conn = db.conn

    order = conn.execute(
        """
        SELECT o.*, c.name AS customer_name, c.email AS customer_email,
               c.phone AS customer_phone, c.city AS customer_city
        FROM orders o
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.order_id = ?
        """,
        (int(order_id),),
    ).fetchone()

    if not order:
        return {
            "encontrado": False,
            "order_id": order_id,
            "mensagem": f"Pedido #{order_id} não encontrado na base da Empório da Música.",
        }

    # Validação de titularidade LGPD (aceita primeiro nome, nome completo, e-mail ou dígitos do telefone)
    conf_norm = normalize_text(confirmacao_cliente)
    conf_digits = re.sub(r"\D", "", confirmacao_cliente or "")

    cust_name_norm = normalize_text(order["customer_name"])
    cust_name_parts = [p for p in cust_name_norm.split() if len(p) >= 3]
    cust_email_norm = normalize_text(order["customer_email"])
    cust_phone_digits = re.sub(r"\D", "", order["customer_phone"] or "")

    verified = False
    if conf_norm:
        if conf_norm == cust_email_norm or conf_norm in cust_name_norm:
            verified = True
        elif any(part in conf_norm.split() for part in cust_name_parts):
            verified = True
    if not verified and len(conf_digits) >= 4 and conf_digits in cust_phone_digits:
        verified = True

    if not verified:
        return {
            "encontrado": True,
            "order_id": order_id,
            "verificado_lgpd": False,
            "instrucao_atendimento": (
                "O pedido existe no sistema, mas para proteger a privacidade do cliente (LGPD - Seção 9), "
                "solicite educadamente que ele confirme seu nome, e-mail ou final do telefone antes de exibir os dados do pedido."
            ),
        }

    items = conn.execute(
        """
        SELECT oi.quantity, p.product_id, p.name, p.price_brl, p.status AS product_status
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        WHERE oi.order_id = ?
        """,
        (int(order_id),),
    ).fetchall()

    status_pt_map = {
        "delivered": "Entregue",
        "shipped": "Enviado / Em transporte",
        "confirmed": "Confirmado (aguardando despacho)",
        "pending": "Pendente de confirmação de pagamento/processamento",
        "cancelled": "Cancelado",
    }

    return {
        "encontrado": True,
        "verificado_lgpd": True,
        "order_id": order["order_id"],
        "cliente": {
            "nome": order["customer_name"],
            "cidade": order["customer_city"],
            "email_mascarado": _mask_email(order["customer_email"]),
        },
        "data_pedido": order["order_date"],
        "status_sistema": order["status"],
        "status_legivel": status_pt_map.get(order["status"], order["status"]),
        "valor_total_brl": order["total_brl"],
        "forma_pagamento": order["payment_method"],
        "codigo_rastreamento": order["tracking_code"],
        "previsao_ou_data_entrega": order["estimated_delivery"],
        "observacoes_pedido": order["notes"],
        "itens": [dict(i) for i in items],
        "orientacoes_politica_aplicavel": (
            "Para dúvidas de devolução/troca deste pedido, consulte também `consultar_politicas_loja`: "
            "arrependimento em compras online é até 7 dias corridos após o recebimento; "
            "troca por defeito na loja até 30 dias da compra (garantia legal CDC de 90 dias a partir do recebimento)."
        ),
    }


def consultar_politicas_loja(pergunta: str) -> dict[str, Any]:
    """Consulta o Manual Oficial de Políticas e Procedimentos da Empório da Música (via RAG híbrido).

    Use sempre para responder sobre: endereço, telefone/WhatsApp, horários de funcionamento,
    formas de pagamento e regras de parcelamento, trocas, devoluções, direito de arrependimento,
    frete (Campo Grande e outras cidades), promoções, garantia, reclamações e LGPD.
    """
    retriever = get_policy_retriever()
    trechos = retriever.search(pergunta, top_k=4)
    return {
        "pergunta_consultada": pergunta,
        "trechos_manual": trechos,
        "notas_padronizacao_institucional": (
            "Nota de consistência documental: o manual registra telefone/WhatsApp geral (67) 3341-4444 "
            "(Capa e Seção 1.2) e linha dedicada de atendimento WhatsApp (67) 3321-4500 (Seção 7); "
            "para e-mail, utilize a grafia válida sem acento: contato@emporiodamusica.com.br."
        ),
    }


AGENT_TOOLS = [
    buscar_catalogo_instrumentos,
    listar_categorias_e_promocoes_ativas,
    consultar_pedido_cliente,
    consultar_politicas_loja,
]
