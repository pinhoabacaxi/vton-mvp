<#
.SYNOPSIS
  Cria um virtualenv, instala dependências e inicia o backend (uvicorn).

USAGE
  Execute no PowerShell a partir da pasta `backend`:
    ./run-backend.ps1

NOTES
  - Requer Python no PATH.
  - Ajuste permissões de execução se necessário: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#>

$ErrorActionPreference = 'Stop'

Write-Host "Criando/atualizando virtualenv .venv..."
python -m venv .venv

Write-Host "Ativando virtualenv..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Atualizando pip e instalando dependências..."
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Iniciando servidor uvicorn na porta 8000 (Ctrl+C para parar)..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
