@echo off
setlocal
where py >nul 2>nul
if %errorlevel% equ 0 goto use_py
where python >nul 2>nul
if %errorlevel% equ 0 goto use_python
echo Prediction CLI needs Python 3.10+ from https://www.python.org/downloads/
pause
exit /b 1
:use_py
py -3 "%~dp0prediction-cli.pyz" %*
exit /b %errorlevel%
:use_python
python "%~dp0prediction-cli.pyz" %*
exit /b %errorlevel%
