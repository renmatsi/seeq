@echo off
cd /d "%~dp0"
if exist "engine\torrentFindr-engine.exe" (start "" "desktop-app\seeq.exe" & exit /b)
where pyw >nul 2>nul
if %errorlevel%==0 (start "" pyw -3 start_desktop.py & exit /b)
where pythonw >nul 2>nul
if %errorlevel%==0 (start "" pythonw start_desktop.py & exit /b)
echo Instale o Python 3.10 ou superior, incluindo Tcl/Tk, e tente novamente.
pause
