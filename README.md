# prospecTHOR

Plataforma web que, a partir da sua localização atual, faz scraping do Google Maps e lista os negócios locais dentro de um raio configurável. Os resultados são salvos em um banco SQLite com deduplicação automática.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python + FastAPI |
| Scraping | Playwright (Chromium headless) |
| Banco de dados | SQLite via aiosqlite |
| Frontend | HTML + CSS + JS (sem framework) |

---

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado
- Python 3.11+

---

## Instalação e execução com `uv`

### 1. Criar o ambiente virtual e instalar dependências

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. Instalar o browser Chromium para o Playwright

```bash
playwright install chromium
```

> O Playwright baixa um binário do Chromium isolado (~170 MB). Esse passo é necessário apenas uma vez.

### 3. Iniciar o servidor

```bash
uvicorn main:app --reload
```

Acesse em: **http://localhost:8000**

---

## Como usar

1. Abra `http://localhost:8000` no navegador
2. Informe o raio de busca em **km** (1–100)
3. Clique em **Buscar Negócios**
4. O navegador solicitará permissão de **geolocalização** — autorize
5. O scraping é iniciado; aguarde (pode levar alguns minutos dependendo do raio)
6. Os resultados aparecem em tabela com: nome, categoria, endereço, telefone, avaliação e site
7. Ao reabrir a página, os negócios já salvos são carregados automaticamente

---

## Estrutura do projeto

```
essena_schrute/
├── main.py          # App FastAPI: rotas e inicialização
├── scraper.py       # Scraping do Google Maps com Playwright
├── database.py      # Schema SQLite e operações de leitura/escrita
├── requirements.txt # Dependências Python
├── businesses.db    # Banco de dados (criado automaticamente na 1ª execução)
└── static/
    └── index.html   # Frontend completo
```

---

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Serve o frontend |
| `POST` | `/scrape` | Inicia o scraping e retorna a lista atualizada |
| `GET` | `/businesses` | Retorna todos os negócios salvos no banco |

### Exemplo de chamada para `/scrape`

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"lat": -23.5505, "lon": -46.6333, "radius_km": 5}'
```

### Resposta

```json
{
  "scraped": 42,
  "new": 8,
  "businesses": [
    {
      "id": 1,
      "place_id": "Pizzaria+Roma_Rua+das+Flores",
      "name": "Pizzaria Roma",
      "category": "Pizzaria",
      "address": "Rua das Flores, 123",
      "phone": "(11) 99999-0000",
      "rating": 4.5,
      "review_count": 312,
      "website": "https://pizzariaroma.com.br",
      "lat": -23.5505,
      "lon": -46.6333,
      "first_seen": "2026-03-30T20:00:00+00:00",
      "last_seen": "2026-03-30T20:00:00+00:00"
    }
  ]
}
```

---

## Banco de dados

O arquivo `businesses.db` é criado automaticamente na raiz do projeto na primeira execução.

### Schema da tabela `businesses`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER PK | Auto-incremento |
| `place_id` | TEXT UNIQUE | Identificador único (nome + endereço ou ID do Google) |
| `name` | TEXT | Nome do negócio |
| `category` | TEXT | Categoria (ex: Restaurante, Farmácia) |
| `address` | TEXT | Endereço completo |
| `phone` | TEXT | Telefone |
| `rating` | REAL | Nota média (0–5) |
| `review_count` | INTEGER | Número de avaliações |
| `website` | TEXT | URL do site |
| `lat` / `lon` | REAL | Coordenadas da busca que originou o registro |
| `first_seen` | TEXT | ISO 8601 — primeira vez mapeado |
| `last_seen` | TEXT | ISO 8601 — última vez encontrado no scraping |

### Deduplicação

Negócios já existentes no banco **não são duplicados**. A inserção usa `INSERT OR IGNORE` com base no `place_id`. Em buscas subsequentes, apenas `last_seen`, `rating` e `review_count` são atualizados.

---

## Observações sobre o scraping

- O Google Maps pode demorar para carregar os resultados dependendo da velocidade da conexão e do tamanho do raio
- **Raios menores** (2–10 km) tendem a retornar resultados mais precisos e rápidos
- Os **seletores CSS** do Google Maps podem mudar sem aviso — se o scraping parar de extrair dados corretamente, verifique e atualize os seletores em `scraper.py`
- O browser roda em modo **headless** (sem interface gráfica). Para depurar o scraping visualmente, altere em `scraper.py`:
  ```python
  browser = await p.chromium.launch(headless=False)
  ```
- O scraping simula um usuário real com locale `pt-BR` e geolocalização injetada

---

## Variáveis e configurações

Não há arquivo `.env` — as configurações relevantes ficam diretamente nos arquivos:

| Configuração | Arquivo | Padrão |
|---|---|---|
| Caminho do banco SQLite | `database.py` → `DB_PATH` | `businesses.db` |
| Máximo de scrolls no feed | `scraper.py` → `range(15)` | 15 tentativas |
| Zoom mínimo/máximo | `scraper.py` → `_zoom_from_radius` | 10–16 |
| Porta do servidor | comando `uvicorn` | 8000 |
