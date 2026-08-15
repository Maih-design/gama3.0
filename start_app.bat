@echo off

cd /d "C:\Users\mai_h\Gama3.0"

call venv\Scripts\activate.bat

start "" cmd /c "python manage.py runserver"

timeout /t 2 /nobreak >nul

start "" http://127.0.0.1:8000

exit