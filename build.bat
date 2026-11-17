@echo off
REM Build and validate the single-file Windows executable for Patient Database.
REM Run from the project directory.

set PYTHON=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe
set APP=PhysioDatabase

"%PYTHON%" -m PyInstaller --noconfirm --clean PhysioDatabase.spec
if errorlevel 1 exit /b 1

"%PYTHON%" scripts\verify_release.py --exe dist\%APP%.exe
if errorlevel 1 exit /b 1

echo.
echo Build finished and validated. Output: dist\%APP%.exe
