@echo off
title Instalacion del proyecto
python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Instalacion terminada. Revisa el archivo .env antes de iniciar.
pause
