"""Pipeline de ingestão, higienização dos CSVs e banco relacional SQLite."""

from __future__ import annotations

import csv
import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from src.config import DATA_DIR

KNOWN_BRANDS = (
    "yamaha",
    "tagima",
    "giannini",
    "rozini",
    "shelby",
    "crafter",
    "martin",
    "taylor",
    "takamine",
    "kala",
    "ohana",
    "kalani",
    "fender",
    "gibson",
    "ibanez",
    "prs",
    "music man",
    "pearl",
    "tama",
    "korg",
    "roland",
    "nord",
)


def normalize_text(value: str | None) -> str:
    """Remove acentos e converte para minúsculas para buscas tolerantes a grafia."""
    if not value:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(value))
    ascii_only = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return ascii_only.lower().strip()


def _detect_product_anomalies(
    name: str,
    description: str,
    status: str,
    stock_quantity: int,
    specs: dict[str, Any],
) -> list[str]:
    """Identifica divergências cadastrais nos dados brutos para transparência no atendimento."""
    notes: list[str] = []
    norm_name = normalize_text(name)
    norm_desc = normalize_text(description)

    name_brands = [b for b in KNOWN_BRANDS if b in norm_name]
    desc_brands = [b for b in KNOWN_BRANDS if b in norm_desc]
    if name_brands and desc_brands and set(name_brands).isdisjoint(desc_brands):
        notes.append(
            f"Divergência cadastral detectada entre título ({', '.join(name_brands).title()}) "
            f"e descrição ({', '.join(desc_brands).title()}); recomenda-se confirmar ficha técnica física."
        )

    if "88 teclas" in norm_desc and str(specs.get("keys", "")) == "61":
        notes.append(
            "Divergência cadastral no número de teclas (descrição cita 88 teclas, especificação técnica registra 61)."
        )

    if "5 cordas" in norm_desc and str(specs.get("strings", "")) == "4":
        notes.append(
            "Divergência cadastral no número de cordas (descrição cita 5 cordas, especificação técnica registra 4)."
        )

    if status == "discontinued" and stock_quantity > 0:
        notes.append(
            "Produto marcado como descontinuado no catálogo apesar de saldo residual no CSV; não deve ser ofertado como ativo."
        )

    return notes


class CatalogDatabase:
    """Gerencia o banco SQLite em memória alimentado e higienizado a partir dos CSVs da loja."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("NORM", 1, normalize_text)
        self._create_schema()
        self._load_all_csvs()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE categories (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            );

            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                price_brl REAL NOT NULL,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                description TEXT,
                stock_quantity INTEGER NOT NULL,
                status TEXT NOT NULL,
                specs_json TEXT,
                created_at TEXT,
                data_quality_notes TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(category_id)
            );

            CREATE TABLE promotions (
                promotion_id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                discount_percent REAL NOT NULL,
                description TEXT,
                is_active INTEGER NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );

            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                city TEXT
            );

            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL,
                total_brl REAL NOT NULL,
                payment_method TEXT NOT NULL,
                tracking_code TEXT,
                estimated_delivery TEXT,
                notes TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            );

            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
            """
        )

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self.data_dir / filename
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return [
                {k.strip(): (v.strip() if v is not None else "") for k, v in row.items()}
                for row in reader
            ]

    def _load_all_csvs(self) -> None:
        # 1. Categorias
        for row in self._read_csv("desafio_tecnico_ai_eng - categories.csv"):
            self.conn.execute(
                "INSERT INTO categories VALUES (?, ?, ?)",
                (int(row["category_id"]), row["name"], row["description"]),
            )

        # 2. Produtos (com validação de JSON specs e auditoria de inconsistências)
        for row in self._read_csv("desafio_tecnico_ai_eng - products.csv"):
            raw_specs = row.get("specs", "{}")
            try:
                specs_dict = json.loads(raw_specs) if raw_specs else {}
            except json.JSONDecodeError:
                specs_dict = {}

            status = row["status"].lower()
            stock = int(row["stock_quantity"])
            anomalies = _detect_product_anomalies(
                name=row["name"],
                description=row["description"],
                status=status,
                stock_quantity=stock,
                specs=specs_dict,
            )

            self.conn.execute(
                """
                INSERT INTO products (
                    product_id, price_brl, name, category_id, description,
                    stock_quantity, status, specs_json, created_at, data_quality_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["product_id"]),
                    round(float(row["price_brl"]), 2),
                    row["name"],
                    int(row["category_id"]),
                    row["description"],
                    stock,
                    status,
                    json.dumps(specs_dict, ensure_ascii=False),
                    row["created_at"],
                    " | ".join(anomalies) if anomalies else None,
                ),
            )

        # 3. Promoções
        for row in self._read_csv("desafio_tecnico_ai_eng - promotions.csv"):
            self.conn.execute(
                "INSERT INTO promotions VALUES (?, ?, ?, ?, ?)",
                (
                    int(row["promotion_id"]),
                    int(row["product_id"]),
                    float(row["discount_percent"]),
                    row["description"],
                    int(row["is_active"]),
                ),
            )

        # 4. Clientes
        for row in self._read_csv("desafio_tecnico_ai_eng - customers.csv"):
            self.conn.execute(
                "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                (
                    int(row["customer_id"]),
                    row["name"],
                    row["phone"],
                    row["email"].lower(),
                    row["city"],
                ),
            )

        # 5. Pedidos
        for row in self._read_csv("desafio_tecnico_ai_eng - orders.csv"):
            self.conn.execute(
                "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(row["order_id"]),
                    int(row["customer_id"]),
                    row["order_date"],
                    row["status"].lower(),
                    round(float(row["total_brl"]), 2),
                    row["payment_method"].lower(),
                    row["tracking_code"] or None,
                    row["estimated_delivery"] or None,
                    row["notes"] or None,
                ),
            )

        # 6. Itens de Pedido
        for row in self._read_csv("desafio_tecnico_ai_eng - order_items.csv"):
            self.conn.execute(
                "INSERT INTO order_items (order_id, quantity, product_id) VALUES (?, ?, ?)",
                (int(row["order_id"]), int(row["quantity"]), int(row["product_id"])),
            )

        self.conn.commit()

    def audit_summary(self) -> dict[str, Any]:
        """Retorna estatísticas do catálogo e das inconsistências auditadas."""
        cur = self.conn.cursor()
        total_products = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        available_products = cur.execute(
            "SELECT COUNT(*) FROM products WHERE status = 'active' AND stock_quantity > 0"
        ).fetchone()[0]
        active_promos = cur.execute(
            "SELECT COUNT(*) FROM promotions WHERE is_active = 1"
        ).fetchone()[0]
        expired_promos = cur.execute(
            "SELECT COUNT(*) FROM promotions WHERE is_active = 0"
        ).fetchone()[0]
        flagged_products = cur.execute(
            "SELECT COUNT(*) FROM products WHERE data_quality_notes IS NOT NULL"
        ).fetchone()[0]
        empty_categories = [
            r["name"]
            for r in cur.execute(
                """
                SELECT c.name
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.category_id
                GROUP BY c.category_id
                HAVING COUNT(p.product_id) = 0
                """
            ).fetchall()
        ]
        return {
            "total_products": total_products,
            "available_products": available_products,
            "active_promotions": active_promos,
            "expired_promotions": expired_promos,
            "flagged_products_with_anomalies": flagged_products,
            "empty_categories": empty_categories,
        }


_db_instance: CatalogDatabase | None = None


def get_catalog_db() -> CatalogDatabase:
    """Retorna instância singleton do banco de dados de catálogo e pedidos."""
    global _db_instance
    if _db_instance is None:
        _db_instance = CatalogDatabase()
    return _db_instance
