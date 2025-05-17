@echo off
echo Instalando dependencias...
pip install -r Requirements.txt
py manage.py runserver
pause
