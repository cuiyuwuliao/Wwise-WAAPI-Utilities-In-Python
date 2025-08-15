@echo off
SETLOCAL

set /p "filePath=drop in a python script that you want to pyinstall. "

:: Check if a file was passed in
IF "%filePath%"=="" (
    echo No file path provided.
    pause
    exit /b
)

:: Get the file name and directory
SET "fileName=%~nx1"
SET "fileDir=%~dp1"

:: Change to the file's directory
cd /d "%~dp0" || (
    echo Failed to change directory to "%fileDir%".
    pause
    exit /b
)

:: Run PyInstaller
pyinstaller --onefile "%filePath%"

:: Pause to see the output
pause
ENDLOCAL