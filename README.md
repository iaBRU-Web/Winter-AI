# Winter AI ❄️

**Multi-paradigm reasoning engine — EN → FR → RW**  
Created by INEZA Aime Bruno, Rwanda

---

## Architecture

Winter runs 7 reasoning layers per query:

| Layer | Engine | Role |
|-------|--------|------|
| 1 | Python | Orchestration & language detection |
| 2 | Prolog | Knowledge search & reasoning |
| 3 | Mercury | Determinism check |
| 4 | OCaml | UTF-8 type validation |
| 5 | LISP | Symbolic tokenization |
| 6 | C++ | Unreal Engine instruction formatting |
| 7 | Schema | Output validation |

## Languages

- **English** — primary
- **Français** — secondary
- **Kinyarwanda** — national language of Rwanda

## API Endpoints

```
POST /api/v1/chats/message       — Chat with Winter AI
POST /api/v1/brain/update        — Update knowledge base
POST /api/v1/knowledge/upload    — Upload new knowledge file
GET  /api/v1/knowledge/list      — List knowledge files
GET  /api/v1/knowledge/{file}    — Read a knowledge file
GET  /api/v1/brain               — Read brain.txt
GET  /api/v1/health              — Health check
GET  /docs                       — Swagger UI
```

## Deploy on Render

1. Push to GitHub
2. Create new Render Web Service → Docker
3. Set `PORT=10000`
4. Deploy ✅

## Knowledge Files

All in `api/info/`:
- `brain.txt` — core knowledge (editable via API)
- `logics.txt` — reasoning rules
- `grammar.txt` — language grammar rules
- `info.txt` — system information
- `dictionary.txt` — trilingual dictionary
