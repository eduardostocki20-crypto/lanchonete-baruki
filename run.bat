@echo off
title Bella Napoli - Pizzaria Artesanal (Python)
echo ========================================================
echo   PIZZARIA BELLA NAPOLI - SISTEMA COMPLETO EM PYTHON
echo ========================================================
echo.
echo 1. Instalando dependencias (Flask)...
py -m pip install -r requirements.txt
echo.
echo 2. Iniciando aplicacao web e banco de dados SQLite...
echo Acesse no seu navegador: http://localhost:5000
echo Painel do Gerente: http://localhost:5000/admin
echo.
py app.py
pause
