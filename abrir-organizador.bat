@echo off
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0"
set "VENV_ACTIVATE=%PROJECT_ROOT%.venv\Scripts\activate.bat"
set "ORGANIZER_EXE=%PROJECT_ROOT%.venv\Scripts\organizer.exe"

cd /d "%PROJECT_ROOT%"

echo.
echo ========================================
echo   Organizador de Carpetas
echo ========================================
echo.

if not exist "%VENV_ACTIVATE%" (
    echo [ERROR] No encontre el entorno virtual local.
    echo.
    echo Falta este archivo:
    echo   "%VENV_ACTIVATE%"
    echo.
    echo Para prepararlo, abri CMD en esta carpeta y ejecuta:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -e ".[dev]"
    echo.
    pause
    exit /b 1
)

call "%VENV_ACTIVATE%"
if errorlevel 1 (
    echo [ERROR] No pude activar el entorno virtual .venv.
    echo.
    echo Proba recrearlo con los comandos de instalacion del README.
    echo.
    pause
    exit /b 1
)

if not exist "%ORGANIZER_EXE%" (
    echo [ERROR] El comando organizer no esta instalado en .venv.
    echo.
    echo Falta este archivo:
    echo   "%ORGANIZER_EXE%"
    echo.
    echo Para instalar la app localmente, ejecuta:
    echo   .venv\Scripts\activate
    echo   pip install -e ".[dev]"
    echo.
    pause
    exit /b 1
)

echo Abriendo el menu guiado...
echo.
organizer menu
set "ORGANIZER_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%ORGANIZER_EXIT_CODE%"=="0" (
    echo [ERROR] El organizador termino con codigo %ORGANIZER_EXIT_CODE%.
    echo Revisa el mensaje anterior para entender que paso.
) else (
    echo Organizador cerrado correctamente.
)
echo.
pause
exit /b %ORGANIZER_EXIT_CODE%
