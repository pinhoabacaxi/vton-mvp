# VTON MVP - Fashion Helper

MVP mobile de Virtual Try-On (VTON) para moda, com backend FastAPI e app React Native/Expo Android.

## Stack

- Backend: Python, FastAPI, Uvicorn
- Mobile: React Native/Expo, Android package `com.anonymous.vtonmvp`
- Deploy alvo do backend: Render Free
- Processamento de imagens: compressao no app e remocao/otimizacao no backend

## Estrutura

```text
backend/   API FastAPI, scraping, processamento de imagem e VTON providers
frontend/  App Expo/React Native e projeto Android gerado
scripts/   Scripts auxiliares locais
```

## Backend local

```bash
python -m pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Variaveis de ambiente do backend

Copie `backend/.env.example` para `backend/.env` apenas no ambiente local. Nao commitar arquivos `.env`.

Principais variaveis:

- `PUBLIC_BACKEND_URL`: URL publica do backend, usada para montar URLs absolutas de `/uploads`.
- `DISABLE_REMBG`: use `true` no Render Free para reduzir memoria.
- `VTON_PROVIDER`: `mock`, `external` ou `replicate`.
- `REPLICATE_API_TOKEN`, `REPLICATE_MODEL`, `REPLICATE_VERSION`: usadas apenas quando o provider Replicate estiver ativo.

## Mobile local

```bash
cd frontend
npm install
npm run start
```

A URL padrao da API fica em `frontend/src/config/api.ts` e tambem em `frontend/app.json` via `extra.apiUrl`.

## Deploy Render

O arquivo `render.yaml` esta preparado para subir o backend a partir da pasta `backend/`.

Depois de criar o servico no Render, configure:

- `PUBLIC_BACKEND_URL=https://seu-servico.onrender.com`
- `DISABLE_REMBG=true` para plano Free
- Chaves do provider VTON somente se usar Replicate/API externa

## Higiene para GitHub

O `.gitignore` da raiz exclui dependencias, ambientes virtuais, uploads temporarios, caches, builds Android, APKs e arquivos `.env`.

Antes de publicar:

```bash
git status --short
git add .
git commit -m "Prepare VTON MVP for GitHub export"
```
