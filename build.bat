@echo off

set PACKAGE_NAME=Resotto
set MAIN_SCRIPT=src\main.py

pyinstaller --onefile --name %PACKAGE_NAME% %MAIN_SCRIPT% --icon images\favicon.ico

mkdir dist\config
mkdir dist\log
if not exist "dist\config\config.json" (
    xcopy src\config\config.json dist\config\ /E /I /Y
)

xcopy README.md dist\ /I /Y
