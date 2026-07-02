@echo off
REM =============================================================================
REM B3 Data Platform — Windows Setup Launcher
REM Detects available shell and delegates to setup.sh
REM =============================================================================

echo.
echo =============================================
echo     B3 Data Platform - Windows Launcher
echo =============================================
echo.

REM Try WSL first
where wsl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Using WSL to run setup...
    wsl bash ./setup.sh %*
    goto :end
)

REM Try Git Bash
if exist "C:\Program Files\Git\bin\bash.exe" (
    echo [INFO] Using Git Bash to run setup...
    "C:\Program Files\Git\bin\bash.exe" ./setup.sh %*
    goto :end
)

REM Try MSYS2
if exist "C:\msys64\usr\bin\bash.exe" (
    echo [INFO] Using MSYS2 to run setup...
    "C:\msys64\usr\bin\bash.exe" ./setup.sh %*
    goto :end
)

echo [ERROR] No compatible shell found!
echo Please install one of:
echo   - WSL (recommended): https://learn.microsoft.com/windows/wsl/install
echo   - Git for Windows: https://git-scm.com/download/win
echo.
pause
exit /b 1

:end
echo.
pause
