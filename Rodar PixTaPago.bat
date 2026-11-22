@echo off
setlocal EnableExtensions
chcp 65001 >nul
title PixTaPago - Inicializador
cd /d "%~dp0"

echo ==================================================
echo   PixTaPago - iniciando backend e frontend
echo ==================================================
echo.

rem ---------- Pre-requisitos ----------
where python >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH. Instale o Python 3.12+ e tente de novo.
  pause & exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Node.js/npm nao encontrado no PATH. Instale o Node.js e tente de novo.
  pause & exit /b 1
)

rem ---------- Backend ----------
pushd backend

if not exist ".venv\Scripts\python.exe" (
  echo [backend] Criando ambiente virtual .venv ...
  python -m venv .venv || (echo [ERRO] Falha ao criar a venv. & popd & pause & exit /b 1)
)

rem Reinstala dependencias so quando requirements.txt mudar
fc /b requirements.txt ".venv\requirements.stamp" >nul 2>&1
if errorlevel 1 (
  echo [backend] Instalando dependencias Python ...
  ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || (echo [ERRO] Falha no pip install. & popd & pause & exit /b 1)
  copy /y requirements.txt ".venv\requirements.stamp" >nul
)

if not exist ".env" (
  echo [backend] Criando .env a partir de .env.example - preencha as credenciais do BB.
  copy /y ".env.example" ".env" >nul
)

popd

rem ---------- Frontend ----------
pushd frontend
if not exist "node_modules" (
  echo [frontend] Instalando dependencias npm - pode demorar na primeira vez ...
  call npm install || (echo [ERRO] Falha no npm install. & popd & pause & exit /b 1)
)
popd

rem ---------- Subir servidores ----------
echo.
echo [backend]  Subindo Flask em http://localhost:5000 ...
start "PixTaPago - Backend (Flask :5000)" /d "%~dp0backend" cmd /k ".venv\Scripts\python.exe app.py"

echo [frontend] Subindo Vite em http://localhost:5173 ...
start "PixTaPago - Frontend (Vite :5173)" /d "%~dp0frontend" cmd /k "npm run dev"

rem Aguarda o frontend responder (ate ~60 s) antes de abrir o navegador
echo Aguardando os servidores ficarem prontos ...
set /a tentativas=0
:esperar
set /a tentativas+=1
curl -s -o nul http://localhost:5173 >nul 2>&1
if not errorlevel 1 goto pronto
if %tentativas% geq 30 goto pronto
timeout /t 2 /nobreak >nul
goto esperar

:pronto
start "" http://localhost:5173

echo.
echo ==================================================
echo   Pronto! Guias disponiveis:
echo.
echo   Painel do estabelecimento (login)
echo     http://localhost:5173/              Dashboard
echo     http://localhost:5173/charges       Cobrancas
echo     http://localhost:5173/charges/new   Gerar cobranca
echo     http://localhost:5173/receipts      Recebimentos
echo     Usuario: demo@pixtapago.com.br   Senha: pix123
echo.
echo   Simulador bancario (sem login)
echo     http://localhost:5173/cliente       Pedro - pagador
echo     http://localhost:5173/dono          Joao  - recebedor
echo.
echo   API: http://localhost:5000/api
echo.
echo   Para parar: feche as janelas "Backend" e "Frontend".
echo ==================================================
echo.
pause
endlocal
