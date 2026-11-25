@echo off
REM ===========================================================================
REM PoisonGuard Unified Runner (Suite & CLI)
REM ===========================================================================

set PATH=C:\Users\Lenovo\AppData\Local\Android\Sdk\platform-tools;%PATH%
set PYTHONPATH=%~dp0src;%PYTHONPATH%
cd /d "%~dp0"

if "%1"=="test" (
    python -m pytest -q tests
    goto :eof
)
if "%1"=="baseline" (
    python scripts\run_baselines_suite.py --target %2
    goto :eof
)
if "%1"=="attack" (
    python scripts\run_baselines_suite.py --target %2
    goto :eof
)
if "%1"=="real" (
    python -m poisonguard.cli %*
    goto :eof
)
if "%1"=="demo" (
    python -m poisonguard.cli %*
    goto :eof
)
if "%1"=="experiment" (
    python -m poisonguard.cli %*
    goto :eof
)
if "%1"=="plot" (
    python -m poisonguard.cli %*
    goto :eof
)
if "%1"=="validate-data" (
    python -m poisonguard.cli %*
    goto :eof
)

python scripts\run_resumable_suite.py %*
