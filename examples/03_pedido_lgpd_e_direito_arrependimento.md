# Cenário 3 — Rastreamento com Validação LGPD + Direito de Arrependimento

> **Objetivo do cenário:** Demonstrar situação não trivial cruzando dados reais do pedido #8 (`consultar_pedido_cliente`), proteção de dados pessoais (LGPD - Seção 9) e aplicação das regras de devolução online (Seção 4.1).

---

### Turno 1
**👤 Cliente:** Oi! Fiz o pedido #8 pela internet, mas acho que me arrependi da compra. Qual o status dele e como funciona se eu quiser devolver?

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (2)</strong> — modelo <code>gemini-3.5-flash-lite</code> (7016 ms)</summary>

- `consultar_pedido_cliente({"order_id": 8})` → *Pedido #8 localizado — aguardando confirmação LGPD* (`0 ms`)
- `consultar_politicas_loja({"pergunta": "Qual é o prazo e o procedimento para devolução por arrependimento de compras feitas pela internet?"})` → *Seções recuperadas: 4. Política de Trocas e Devoluções > 4.1 Direito de Arrependimento (Compras Online) | 7. Atendimento via WhatsApp > 7.3 Situações Especiais* (`782 ms`)

</details>

**🎸 Empório da Música:**

Olá! Tudo bem? 

Para que eu possa consultar os detalhes e o status do seu pedido #8 com segurança (conforme as diretrizes de proteção de dados), você poderia por gentileza confirmar o seu **nome completo, e-mail ou telefone** cadastrado na compra?

Assim que você confirmar, já te passo todas as informações do pedido. 

Enquanto isso, sobre a devolução por arrependimento em compras feitas pela internet, o procedimento funciona assim:
- **Prazo:** Você pode solicitar a devolução em até **7 (sete) dias corridos** após o recebimento do produto, sem precisar justificar.
- **Condições:** O instrumento precisa estar na embalagem original, sem sinais de uso e acompanhado de todos os itens.
- **Frete:** O frete de devolução por arrependimento fica por conta da loja.
- **Reembolso:** É realizado na mesma forma de pagamento original em até 10 dias úteis após o recebimento e conferência do produto em nosso estoque.

Fico no aguardo da sua confirmação para te ajudar com o pedido #8!

---

### Turno 2
**👤 Cliente:** Claro! Meu nome é Ana Carolina Ferreira.

<details>
<summary>🔍 <strong>Ferramentas acionadas pelo Agente (2)</strong> — modelo <code>gemini-3.5-flash-lite</code> (9432 ms)</summary>

- `consultar_pedido_cliente({"confirmacao_cliente": "Ana Carolina Ferreira", "order_id": 8})` → *Pedido #8 validado (Enviado / Em transporte)* (`0 ms`)
- `consultar_politicas_loja({"pergunta": "direito de arrependimento trocas e devolucoes frete prazo estorno"})` → *Seções recuperadas: 4. Política de Trocas e Devoluções > 4.1 Direito de Arrependimento (Compras Online) | 4. Política de Trocas e Devoluções > 4.3 Trocas por Preferência* (`857 ms`)

</details>

**🎸 Empório da Música:**

Obrigado pela confirmação, Ana Carolina! Tudo certinho por aqui com a verificação de segurança.

Sobre o seu **pedido #8** (que contém o **Kala KA-C Concert Mogno**, no valor de **R$ 349,90**):
- **Status atual:** **Enviado / Em transporte** 
- **Código de rastreamento:** `BRJL5544332BR`
- **Previsão de entrega:** 28/02/2026

Como você comentou que se arrependeu da compra, fique super tranquila! Como é uma compra feita pela internet, você está totalmente amparada pelo **Direito de Arrependimento**:
1. Você pode solicitar a devolução em até **7 (sete) dias corridos** a contar da data de recebimento do instrumento.
2. O instrumento precisará estar na embalagem original, sem sinais de uso e acompanhado de todos os itens.
3. O **frete de devolução é por nossa conta**! Nós te enviamos as instruções de postagem assim que o pacote for entregue e você formalizar o pedido de devolução.
4. O reembolso do valor (R$ 349,90) é feito na mesma forma de pagamento original em até 10 dias úteis após o produto retornar ao nosso estoque e passar pela conferência.

Como o pedido já está a caminho, você pode aguardar a chegada e, logo após receber, entrar em contato conosco novamente para iniciarmos o processo de logística reversa de devolução, combinado? 

Se precisar de qualquer outra ajuda ou tiver alguma dúvida, é só me chamar!

---
