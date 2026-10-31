@echo off
REM Build a single-file Windows executable for Patient Database Dashboard.
REM Run from the project directory.

set PYTHON=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe
set APP=PatientDatabase
set ENTRY=main.py

"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name %APP% ^
  --add-data "assets;assets" ^
  --add-data "version.py;." ^
  --hidden-import customtkinter ^
  --hidden-import PIL ^
  --hidden-import fitz ^
  --hidden-import openpyxl ^
  --hidden-import darkdetect ^
  %ENTRY%

echo.
echo Build finished. Output: dist\%APP%.exe
