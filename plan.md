# Redesenho Moderno, Simples e Eficiente do CrimesNews

Este plano propõe reestruturar o projeto **CrimesNews** para superar as limitações atuais de bloqueio (Cloudflare/Google bot detection), remover dependências excessivamente pesadas e lentas (como spaCy para processamento em português) e adotar uma interface de usuário moderna baseada em **Streamlit** (alinhada à configuração original do Dockerfile).

---

## 🛠️ Nova Arquitetura Proposta (Fora da Caixa)

O novo fluxo de funcionamento resolve os problemas de bloqueio e lentidão através de três otimizações principais:

1. **Busca Direta Otimizada via Google News (Query Grouping):**
   Em vez de buscar termos genéricos (ex: "homicídio") e baixar centenas de matérias de todo o país para identificar a cidade nelas, nós agruparemos os municípios em pequenos blocos (ex: 15 municípios por vez) e faremos uma query estruturada usando operadores booleanos (`OR`):
   ```
   "homicídio" ("Cidade A" OR "Cidade B" OR "Cidade C" ...)
   ```
   Isso reduz o volume de requisições de centenas para pouquíssimas queries focadas, retornando apenas as notícias que de fato contêm as cidades de interesse.

2. **Detecção Inteligente Sem spaCy (Regex/Match de Substrings):**
   Dado que temos uma lista fechada de municípios para monitorar, não precisamos carregar um modelo de Machine Learning/NLP pesado como o `pt_core_news_sm` do spaCy (que muitas vezes erra a classificação de nomes de cidades). Usaremos busca por palavra-chave exata ou limites de palavras (`\bCidade\b`) diretamente sobre o texto. Isso reduz o tempo de processamento em 99% e remove a necessidade de downloads adicionais.

3. **Extração de Texto Eficiente com Trafilatura & Googlenewsdecoder:**
   * Se o nome do município já estiver presente no título ou snippet do RSS, **a notícia é classificada imediatamente** sem necessidade de fazer requisição HTTP à página web de destino (evitando 100% de bloqueios de Cloudflare ou Paywalls para essas matérias).
   * Para os casos em que precisamos ler a página inteira, usaremos o `googlenewsdecoder` para obter a URL limpa de destino e o `trafilatura` (uma biblioteca moderna de extração de texto estruturado) para baixar o corpo limpo do texto, que é muito mais rápida e eficiente que o BeautifulSoup bruto.

4. **Interface Streamlit Premium:**
   Criaremos um arquivo `app.py` com uma interface Web moderna, dinâmica e elegante usando **Streamlit**, permitindo rodar localmente ou via Docker, ver os logs de processamento em tempo real, filtrar resultados diretamente na tela e fazer o download do arquivo Excel estruturado.

---

## ⚙️ Alterações Propostas

### Dependências (`pyproject.toml`)

* Remover `spacy`.
* Adicionar `googlenewsdecoder` (para traduzir as URLs do Google News).
* Adicionar `trafilatura` (para extração moderna e limpa de textos em páginas web).
* Adicionar `streamlit` (para a interface web).

---

### Core e Regras de Negócio (`Core.py`)

* Reescrever a função `executar` para implementar o agrupamento das cidades por `OR`.
* Substituir o pipeline do `spaCy` por uma busca direta das strings de municípios no título e texto extraído.
* Usar `googlenewsdecoder` e `trafilatura` para os scrapes necessários, removendo o loop complexo de BeautifulSoup.

---

### Interfaces do Usuário (UI)

* **[NEW] `app.py`**: Criar uma interface web moderna com Streamlit.
* **[MODIFY] `CrimesNews-Cli.py`**: Adaptar a CLI para chamar o novo core simplificado.
* **[DELETE] `CrimesNews-Gui.py`**: Remover a antiga interface Tkinter.
