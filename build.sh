#!/bin/bash

PACKAGE_NAME="Resotto"
MAIN_SCRIPT="src/main.py"

pyinstaller --onefile --name "$PACKAGE_NAME" "$MAIN_SCRIPT" --icon "images/favicon.ico"

mkdir -p dist/config
mkdir -p dist/log

if [ ! -f "dist/config/config.json" ]; then
    cp src/config/config.json dist/config/
fi
cp README.md dist/.
