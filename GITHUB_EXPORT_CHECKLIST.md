# GitHub Export Checklist

Este projeto esta preparado para publicacao no GitHub desde que apenas arquivos rastreaveis sejam commitados.

## Nao publicar

- `backend/.venv/`
- `frontend/node_modules/`
- `backend/uploads/`
- `frontend/android/app/build/`
- `frontend/android/.gradle/`
- `*.apk` e `*.aab`
- `.env` e `.env.*`
- pasta acidental `Fashion Helper/`

## Publicar

- Codigo fonte de `backend/`
- Codigo fonte de `frontend/`
- `render.yaml`
- `README.md`
- `.gitignore`
- `.gitattributes`
- `backend/.env.example`

## Sequencia sugerida

```bash
git status --short --ignored
git add .
git commit -m "Prepare VTON MVP for GitHub export"
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

## Observacao

Se o push completo ainda ficar pesado, publique primeiro apenas:

```bash
git add .gitignore .gitattributes README.md render.yaml backend
```
