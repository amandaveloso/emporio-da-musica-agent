# Cenário 4 — Promoção Ativa Não Cumulativa com PIX + Produto Fora de Estoque

> **Objetivo do cenário:** Demonstrar aplicação estrita da Seção 6.2 (promoção ativa de 18% no Crafter HT-100 não acumula com 5% do PIX) e da Seção 7.3 (Giannini GF-3D com estoque zero sugerindo alternativas disponíveis).

---

### Turno 1
**👤 Cliente:** O violão Crafter HT-100 está em promoção? Se eu pagar à vista no PIX ganho mais 5% em cima?

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (2)</strong> — modelo <code>gemini-3.5-flash</code> (8631 ms)</summary>

- `buscar_catalogo_instrumentos({"termo_busca": "Crafter HT-100"})` → *1 instrumento(s) retornado(s): Crafter HT-100 Folk Aço Natural* (`3 ms`)
- `consultar_politicas_loja({"pergunta": "desconto pix cumulativo com promocao"})` → *Seções recuperadas: 6. Promoções e Descontos > 6.2 Regras de Promoções | 3. Formas de Pagamento* (`963 ms`)

</details>

**🎸 Empório da Música:**

Sim, o violão **Crafter HT-100 Folk Aço Natural** está em promoção! 🎸

Confira os detalhes dos valores:
* **Preço original de tabela:** R$ 2.399,00
* **Desconto da promoção (Desconto Exclusivo):** 18%
* **Preço promocional:** R$ 1.967,18 (ou em até 12x de R$ 163,93 sem juros no cartão de crédito)

### Sobre o desconto no PIX:
Sobre a sua dúvida do PIX: pelas políticas da loja (Seção 6.2 do nosso manual), o **desconto de 5% no PIX não é cumulativo com itens que já possuem promoção ativa**. 

Portanto, o valor no PIX permanece no valor promocional de **R$ 1.967,18**, que já está com um excelente desconto! Temos 3 unidades em estoque no momento. 

Se quiser garantir o seu ou tiver qualquer outra dúvida sobre o instrumento, é só avisar!

---

### Turno 2
**👤 Cliente:** E o Giannini GF-3D Sunburst, vocês têm pronta entrega?

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (1)</strong> — modelo <code>gemini-3.5-flash-lite</code> (6663 ms)</summary>

- `buscar_catalogo_instrumentos({"termo_busca": "Giannini GF-3D Sunburst"})` → *1 instrumento(s) retornado(s): Giannini GF-3D Dreadnought Sunburst* (`1 ms`)

</details>

**🎸 Empório da Música:**

O **Giannini GF-3D Dreadnought Sunburst** consta no nosso catálogo, mas infelizmente ele está **temporariamente sem estoque** no momento (quantidade: 0). 

Como ele não está disponível para pronta entrega agora, se você quiser posso te indicar algumas alternativas incríveis de violões com cordas de aço e ótima pegada que temos à pronta entrega aqui na loja:

* **Shelby SGD-195E Elétrico Aço Sunburst** (R$ 799,00 ou até 7x de R$ 114,14 sem juros / R$ 759,05 no PIX) — já vem com captação e afinador integrado!
* **Tagima Dallas Tuner Aço Natural** (R$ 749,00 ou até 7x de R$ 107,00 sem juros / R$ 711,55 no PIX) — excelente custo-benefício e timbre brilhante.

O que acha de alguma dessas opções?

---
