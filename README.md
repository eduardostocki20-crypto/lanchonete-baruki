# 🍕 Bella Napoli - Sistema Web Completo da Pizzaria (100% Python)

Um sistema completo de pizzaria desenvolvido em **Python (Flask)** com banco de dados **SQLite** integrado, cardápio digital dinâmico, carrinho de compras, rastreamento de pedidos em tempo real e um **Painel de Controle Administrativo (Admin)** para a cozinha e gerência.

---

## 📁 Estrutura do Projeto

```
pizzaria-python/
│
├── app.py                     # Aplicação Principal Flask, Rotas, Sessões e APIs
├── database.py                # Criação e sementeira automática do SQLite (pizzaria.db)
├── requirements.txt           # Dependências (Flask)
├── run.bat                    # Script para iniciar com 1 clique no Windows
│
├── static/
│   ├── css/style.css          # Estilos personalizados, animações e efeitos
│   └── js/main.js             # Scripts do cliente e ícones
│
└── templates/
    ├── base.html              # Layout base com barra de avisos, topo e rodapé
    ├── index.html             # Página Inicial (Hero, diferenciais, destaques)
    ├── menu.html              # Cardápio com filtros de categoria e modal de customização
    ├── cart.html              # Carrinho de compras, cálculo de frete e checkout
    ├── order_tracking.html    # Acompanhamento do status do pedido em tempo real + WhatsApp
    └── admin.html             # Painel Gerencial (pedidos, faturamento e cardápio)
```

---

## ⚡ Como Rodar o Projeto

### Opção 1: Com dois cliques (Windows)
Dê dois cliques no arquivo **`run.bat`**. Ele instalará as dependências se necessário e iniciará o servidor automaticamente!

### Opção 2: Pelo Terminal / PowerShell
1. Abra o terminal na pasta do projeto:
   ```bash
   cd "C:\Users\Precode 01\.gemini\antigravity\scratch\pizzaria-python"
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Inicie o servidor:
   ```bash
   python app.py
   ```
4. Abra o navegador em: **`http://localhost:5000`**

---

## 🌟 Principais Recursos

1. **Cardápio Dinâmico via SQLite (`/cardapio`):**
   - Produtos e categorias lidos diretamente do banco de dados relacional.
   - Modal interativo para escolha de tamanho (*Média, Grande, Família*) e bordas recheadas (*Catupiry Original, Cheddar, Chocolate*).
2. **Carrinho de Compras em Sessão (`/carrinho`):**
   - Controle dinâmico de quantidades, remoção e cálculo automático de subtotal e taxa de entrega.
   - Alternância entre **Entrega em domicílio** e **Retirada no balcão**.
   - Seleção de método de pagamento (PIX, Cartão de Crédito/Débito, Dinheiro).
3. **Rastreamento de Pedido em Tempo Real (`/pedido/<id>`):**
   - Barra de progresso visual com 4 etapas: *Recebido ➔ No Forno ➔ A Caminho ➔ Entregue*.
   - Botão para enviar uma cópia formatada do pedido diretamente para o WhatsApp do restaurante.
4. **Painel do Gerente / Cozinha (`/admin`):**
   - Métricas em tempo real: faturamento acumulado, pedidos pendentes e total de vendas.
   - Tabela de pedidos com troca instantânea de status.
   - Cadastro de novos itens no cardápio e botão de pausa/ativação rápida de produtos.
