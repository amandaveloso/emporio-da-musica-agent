# Cenário 2 — Preço do Takamine GD20 (Promoção Expirada) + Endereço e Horário

> **Objetivo do cenário:** Demonstrar tratamento de promoção expirada (`is_active = 0` no Takamine GD20), cálculo de 5% no PIX e combinação com consulta ao RAG institucional (`consultar_politicas_loja`) para endereço e expediente.

---

### Turno 1
**👤 Cliente:** Quanto custa o Takamine GD20? Um amigo disse que viu ele com 12% de desconto na Oferta Especial, ainda vale?

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (1)</strong> — modelo <code>gemini-3.5-flash</code> (6116 ms)</summary>

- `buscar_catalogo_instrumentos({"termo_busca": "Takamine GD20"})` → *1 instrumento(s) retornado(s): Takamine GD20 Dreadnought Natural* (`4 ms`)

</details>

**🎸 Empório da Música:**

O **Takamine GD20 Dreadnought Natural** está custando **R$ 2.199,00** (preço de tabela atual).

Sobre a promoção de 12% de desconto da campanha *Oferta Especial*, ela **já expirou** e não está mais ativa. No momento, o valor vigente do instrumento é o preço regular.

No entanto, temos ótimas condições de pagamento para você levar esse baita violão com tampo sólido em cedro:

- **Pagamento no PIX (à vista):** **R$ 2.089,05** (com 5% de desconto exclusivo para pagamento à vista fora de promoção).
- **Cartão de Crédito:** Em até **12x de R$ 183,25 sem juros**.

Temos **5 unidades disponíveis em estoque** prontas para entrega! Se quiser garantir o seu ou tiver qualquer outra dúvida sobre o modelo, é só me chamar.

---

### Turno 2
**👤 Cliente:** Entendi! Qual o endereço e horário de funcionamento da loja para eu ir testar ele pessoalmente?

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (1)</strong> — modelo <code>gemini-3.5-flash-lite</code> (6593 ms)</summary>

- `consultar_politicas_loja({"pergunta": "Qual é o endereço e horário de funcionamento da loja?"})` → *Seções recuperadas: 2. Horário de Funcionamento | 7. Atendimento via WhatsApp > 7.1 Diretrizes de Atendimento* (`861 ms`)

</details>

**🎸 Empório da Música:**

Será um prazer receber você aqui na loja para testar o Takamine GD20 pessoalmente! 🎸

Nós ficamos na **Rua 14 de Maio, 3200 — Centro, Campo Grande - MS** (CEP 79202-333).

O nosso horário de funcionamento é:
- **Segunda a Sexta-feira:** das 09:00 às 18:00
- **Sábado:** das 09:00 às 13:00
- **Domingos e Feriados:** Fechado

Vem tomar um café com a gente e conferir esse som de perto! Se precisar de alguma informação no caminho, é só chamar.

---
