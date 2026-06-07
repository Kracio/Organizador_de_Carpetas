@echo off
setlocal
chcp 65001 >nul

set "PROJECT_ROOT=%~dp0..\"
cd /d "%PROJECT_ROOT%"

echo.
echo ========================================
echo   Build futuro: OrganizadorDeCarpetas.exe
echo ========================================
echo.

if not exist "%PROJECT_ROOT%.venv\Scripts\activate.bat" (
    echo [ERROR] No encontré .venv\Scripts\activate.bat.
    echo.
    echo Prepará el entorno local antes de empaquetar:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -e ".[dev,packaging]"
    echo.
    pause
    exit /b 1
)

call "%PROJECT_ROOT%.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] No pude activar el entorno virtual .venv.
    echo.
    pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%.venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller no está instalado en .venv.
    echo.
    echo Instalá las dependencias de empaquetado con:
    echo   pip install -e ".[dev,packaging]"
    echo.
    pause
    exit /b 1
)

echo Este comando genera dist\OrganizadorDeCarpetas.exe.
echo No lo ejecutes si sólo querés usar el launcher local.
echo.

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name OrganizadorDeCarpetas ^
  --paths "%PROJECT_ROOT%src" ^
  "%PROJECT_ROOT%packaging\run_menu.py"

set "BUILD_EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%BUILD_EXIT_CODE%"=="0" (
    echo [ERROR] El build terminó con código %BUILD_EXIT_CODE%.
) else (
    echo Build finalizado. Ejecutable esperado:
    echo   %PROJECT_ROOT%dist\OrganizadorDeCarpetas.exe
)
echo.
pause
exit /b %BUILD_EXIT_CODE%
