# Plano: Plataforma de Scraping de Negócios Locais

## Estrutura de Arquivos

```
essena_schrute/
├── main.py           # FastAPI app + rotas
├── scraper.py        # Lógica de scraping com Playwright
├── database.py       # Operações SQLite
├── requirements.txt
└── static/
    └── index.html    # Frontend completo (HTML + CSS + JS)
```

---

## 1. `requirements.txt`

```
fastapi
uvicorn[standard]
playwright
aiosqlite
```

---

## 2. `database.py`

### Schema SQLite

```sql
CREATE TABLE IF NOT EXISTS businesses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id     TEXT UNIQUE,          -- identificador único do Google Maps
    name         TEXT NOT NULL,
    category     TEXT,
    address      TEXT,
    phone        TEXT,
    rating       REAL,
    review_count INTEGER,
    website      TEXT,
    lat          REAL,
    lon          REAL,
    first_seen   TEXT,                 -- ISO datetime
    last_seen    TEXT                  -- ISO datetime
);
```

### Funções
- `init_db()` → cria tabela se não existir
- `upsert_business(business_dict)` → INSERT OR IGNORE (por place_id), atualiza last_seen se já existir
- `get_all_businesses()` → retorna todos os registros ordenados por last_seen DESC

---

## 3. `scraper.py`

### Estratégia de Scraping

**URL de busca:**
```
https://www.google.com/maps/search/negócios+locais/@{lat},{lon},{zoom}z
```

**Cálculo de zoom a partir do raio (km):**
```python
import math
zoom = round(14 - math.log2(max(radius_km, 0.5) / 2))
zoom = max(10, min(16, zoom))
```

**Fluxo do Playwright:**
1. Lançar browser (chromium, headless=True)
2. Navegar para a URL com coordenadas + zoom
3. Aguardar seletor do painel de resultados: `div[role="feed"]`
4. **Scroll loop:** rolar o painel para carregar mais resultados até não ter novos itens
5. Coletar todos os cards do feed: seletor `a.hfpxzc` (link de cada negócio)
6. Para cada card: extrair `aria-label` como nome, clicar para abrir detalhe
7. No painel de detalhe, extrair:
   - Nome: `h1.DUwDvf`
   - Categoria: `button.DkEaL`
   - Endereço: `button[data-item-id="address"]` → `aria-label`
   - Telefone: `button[data-item-id^="phone"]` → `aria-label`
   - Website: `a[data-item-id="authority"]` → `href`
   - Rating: `div.F7nice span[aria-hidden="true"]`
   - Nº de reviews: `div.F7nice span[aria-label$="reviews"]`
   - place_id: extraído da URL atual (`/place/.../` → hash ou nome como fallback)
8. Fechar browser, retornar lista de dicts

**Deduplicação:** gerida no `database.py` via `INSERT OR IGNORE` + `UPDATE last_seen`

---

## 4. `main.py`

### Rotas FastAPI

| Método | Path        | Descrição |
|--------|-------------|-----------|
| GET    | `/`         | Serve `static/index.html` |
| POST   | `/scrape`   | Body: `{lat, lon, radius_km}` → scrapa, salva no DB, retorna lista |
| GET    | `/businesses` | Retorna todos os negócios do DB |

**Modelo Pydantic para `/scrape`:**
```python
class ScrapeRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float
```

**Startup:** chama `init_db()` via `lifespan`

---

## 5. `static/index.html`

### Interface

```
┌─────────────────────────────────┐
│  Negócios Locais                │
│                                 │
│  Raio de busca: [___] km        │
│                                 │
│  [  Buscar Negócios  ]          │
│                                 │
│  ── Resultados ──               │
│  Nome | Cat. | Endereço | Tel   │
│  ...                            │
└─────────────────────────────────┘
```

### Lógica JS
1. Ao clicar "Buscar": `navigator.geolocation.getCurrentPosition()`
2. POST `/scrape` com `{lat, lon, radius_km}`
3. Exibir spinner durante scraping
4. Renderizar tabela com os resultados retornados
5. Tratar erros (geolocalização negada, timeout, etc.)

---

## Ordem de Implementação

1. `requirements.txt`
2. `database.py`
3. `scraper.py`
4. `main.py`
5. `static/index.html`
6. Instruções de execução no terminal

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload
```
