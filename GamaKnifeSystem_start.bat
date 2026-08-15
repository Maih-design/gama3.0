@echo off

cd /d "C:\Users\mai_h\Gama3.0"

call venv\Scripts\activate.bat

timeout /t 1 /nobreak >nul

start "" http://127.0.0.1:8000

python manage.py runserver