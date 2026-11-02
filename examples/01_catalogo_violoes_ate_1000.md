# Cenário 1 — Consulta de Catálogo com Filtro de Preço e Recomendação

> **Objetivo do cenário:** Demonstrar consulta estruturada (`buscar_catalogo_instrumentos`) filtrando violões disponíveis até R$ 1.000,00 (excluindo automaticamente itens sem estoque ou descontinuados) e continuidade de contexto.

---

### Turno 1
**👤 Cliente:** Olá! Quais opções de violões disponíveis custando até R$ 1000?

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (1)</strong> — modelo <code>gemini-3.5-flash</code> (10406 ms)</summary>

- `buscar_catalogo_instrumentos({"preco_max": 1000, "termo_busca": "violão"})` → *13 instrumento(s) retornado(s): Tagima Memphis AC-39 Nylon Natural, Rozini RC-104 Nylon Estudante, Shelby SN-100 Folk Aço Preto...* (`10 ms`)

</details>

**🎸 Empório da Música:**

Olá! Temos excelentes opções de violões disponíveis em nosso catálogo por até R$ 1.000,00! 🎸

Aqui estão algumas das nossas principais recomendações (para pagamento fora de promoção, garantimos **5% de desconto no PIX**):

---

### 🎵 **Violões de Corda de Nylon (Clássicos / Estudo)**

1. **Tagima Memphis AC-39 Nylon Natural**
   - **Preço:** R$ 429,90 *(ou R$ 408,40 no PIX)*
   - **Parcelamento:** Até 5x de R$ 85,98 sem juros
   - **Destaque:** Perfeito para iniciantes, corpo leve e super confortável para estudos.

2. **Rozini RC-104 Nylon Estudante**
   - **Preço:** R$ 459,90 *(ou R$ 436,90 no PIX)*
   - **Parcelamento:** Até 5x de R$ 91,98 sem juros
   - **Destaque:** Produzido com madeiras nacionais (tampo em Spruce), ótimo acabamento.

3. **Yamaha C40 Nylon Natural**
   - **Preço:** R$ 599,90 *(ou R$ 569,90 no PIX)*
   - **Parcelamento:** Até 6x de R$ 99,98 sem juros
   - **Destaque:** Um dos violões de estudo mais recomendados do mundo, com ótima projeção.

4. **Giannini GN-15 Nylon Cedro Natural**
   - **Preço:** R$ 689,00 *(ou R$ 654,55 no PIX)*
   - **Parcelamento:** Até 6x de R$ 114,83 sem juros
   - **Destaque:** Tampo em cedro, oferecendo uma sonoridade mais quente e encorpada.

5. **Yamaha C70 Nylon Natural**
   - **Preço:** R$ 849,00 *(ou R$ 806,55 no PIX)*
   - **Parcelamento:** Até 8x de R$ 106,12 sem juros
   - **Destaque:** Nível intermediário com tampo em Spruce sólido e acabamento de alta qualidade.

---

### 🎸 **Violões de Corda de Aço (Folk / Dreadnought / Elétrico)**

1. **Shelby SN-100 Folk Aço Preto**
   - **Preço:** R$ 549,00 *(ou R$ 521,55 no PIX)*
   - **Parcelamento:** Até 6x de R$ 91,50 sem juros
   - **Destaque:** Visual moderno em preto e timbre versátil.

2. **Giannini GF-1R Aço Folk Sunburst**
   - **Preço:** R$ 579,90 *(ou R$ 550,90 no PIX)*
   - **Parcelamento:** Até 6x de R$ 96,65 sem juros
   - **Destaque:** Tampo em Spruce e acabamento Sunburst clássico.

3. **Yamaha F310 Aço Natural**
   - **Preço:** R$ 699,90 *(ou R$ 664,90 no PIX)*
   - **Parcelamento:** Até 6x de R$ 116,65 sem juros
   - **Destaque:** Um dos modelos Folk mais vendidos da Yamaha, ideal para iniciantes e intermediários.

4. **Tagima Dallas Tuner Aço Natural**
   - **Preço:** R$ 749,00 *(ou R$ 711,55 no PIX)*
   - **Parcelamento:** Até 7x de R$ 107,00 sem juros
   - **Destaque:** Aço com afinador integrado e som brilhante.

5. **Shelby SGD-195E Elétrico Aço Sunburst**
   - **Preço:** R$ 799,00 *(ou R$ 759,05 no PIX)*
   - **Parcelamento:** Até 7x de R$ 114,14 sem juros
   - **Destaque:** Eletroacústico com captação e afinador embutido, perfeito para tocar amplificado!

6. **Tagima Woodstock Dreadnought Natural**
   - **Preço:** R$ 899,00 *(ou R$ 854,05 no PIX)*
   - **Parcelamento:** Até 8x de R$ 112,38 sem juros
   - **Destaque:** Corpo amplo com grave e projeção impressionantes.

---

Se quiser saber mais detalhes de algum modelo ou precisar de ajuda para escolher entre **nylon** ou **aço**, é só chamar! Qual estilo musical você pretende tocar? 🎶

---

### Turno 2
**👤 Cliente:** Estou começando do zero e queria cordas de nylon. Qual desses você me indica e como fica no PIX ou parcelado?

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (1)</strong> — modelo <code>gemini-3.5-flash</code> (6507 ms)</summary>

- `buscar_catalogo_instrumentos({"preco_max": 1000, "termo_busca": "Nylon", "categoria": "Violões"})` → *5 instrumento(s) retornado(s): Tagima Memphis AC-39 Nylon Natural, Rozini RC-104 Nylon Estudante, Yamaha C40 Nylon Natural...* (`3 ms`)

</details>

**🎸 Empório da Música:**

Que excelente escolha começar pelas **cordas de nylon**! Para quem está dando os primeiros passos, o nylon é infinitamente mais confortável nos dedos, evita dores no início e facilita muito a adaptação para formar os primeiros acordes.

Aqui estão as minhas **2 principais recomendações** para quem está começando do zero:

---

### 🥇 1. A Escolha Garantida: **Yamaha C40 Nylon Natural**
É o violão de estudo **mais recomendado por professores no mundo todo**. Ele mantém a afinação muito bem, tem uma maciez excelente no braço e uma projeção de som equilibrada. Se você quer um instrumento para aprender sem frustrações e que vai te acompanhar por anos, este é a melhor escolha!

- **Preço de Tabela:** R$ 599,90
- **No PIX (com 5% de desconto):** **R$ 569,90** à vista
- **Parcelado no Cartão:** **6x de R$ 99,98 sem juros** (total R$ 599,90)

---

### 🥈 2. O Melhor Custo-Benefício: **Tagima Memphis AC-39 Nylon Natural**
Se a ideia for gastar o mínimo possível para começar sem abrir mão da qualidade, o Memphis AC-39 é super leve, bem acabado e perfeito para longas sessões de treino.

- **Preço de Tabela:** R$ 429,90
- **No PIX (com 5% de desconto):** **R$ 408,40** à vista
- **Parcelado no Cartão:** **5x de R$ 85,98 sem juros** (total R$ 429,90)

---

### 📌 Resumo dos Valores para Comparação:

| Modelo | Preço de Tabela | **À vista no PIX (5% OFF)** | **Parcelado sem juros** |
| :--- | :---: | :---: | :---: |
| **Tagima Memphis AC-39** | R$ 429,90 | **R$ 408,40** | 5x de R$ 85,98 |
| **Rozini RC-104** | R$ 459,90 | **R$ 436,90** | 5x de R$ 91,98 |
| **Yamaha C40** *(Recomendado)* | R$ 599,90 | **R$ 569,90** | 6x de R$ 99,98 |
| **Giannini GN-15** | R$ 689,00 | **R$ 654,55** | 6x de R$ 114,83 |
| **Yamaha C70** | R$ 849,00 | **R$ 806,55** | 8x de R$ 106,12 |

Qual deles tem mais a ver com o que você está planejando investir? Se quiser conferir de perto ou tirar alguma dúvida, fico à disposição! 🎸

---
