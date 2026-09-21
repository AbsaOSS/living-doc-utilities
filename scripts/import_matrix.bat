@echo off
rem Import matrix for Windows: builds the wheel, installs it into three clean virtual environments
rem (none, github, html) and proves which modules import and which need an extra.
rem Run scripts\import_matrix.bat from cmd or PowerShell; set PYTHON to choose the interpreter.

setlocal EnableExtensions
if not defined PYTHON set "PYTHON=python"
set "CHECK=%~dp0import_matrix_check.py"
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "WORK=%TEMP%\import-matrix-%RANDOM%%RANDOM%"

mkdir "%WORK%" || exit /b 1
call :run
set "RESULT=%ERRORLEVEL%"
rmdir /s /q "%WORK%" >nul 2>&1
exit /b %RESULT%

:run
"%PYTHON%" "%CHECK%" version "%ROOT%" > "%WORK%\version.txt" || exit /b 1
set /p VERSION=<"%WORK%\version.txt"

echo == Building the wheel (version %VERSION%)
"%PYTHON%" "%CHECK%" copy-sources "%ROOT%" "%WORK%\src" || exit /b 1
"%PYTHON%" -m build --wheel --outdir "%WORK%\dist" "%WORK%\src" > "%WORK%\build.log" 2>&1 || (type "%WORK%\build.log" & exit /b 1)

set "COUNT=0"
for %%W in ("%WORK%\dist\living_doc_utilities-%VERSION%-*.whl") do (
  set /a COUNT+=1
  set "WHEEL=%%~fW"
)
if not "%COUNT%"=="1" (
  echo ::error::expected exactly one living_doc_utilities-%VERSION%-*.whl, found: 1>&2
  dir /b "%WORK%\dist" 1>&2
  exit /b 1
)
for %%W in ("%WHEEL%") do echo Built %%~nxW

"%PYTHON%" "%CHECK%" check-wheel "%WHEEL%" || exit /b 1

for %%M in (none github html) do call :check_environment %%M || exit /b 1
echo == Import matrix passed
exit /b 0

:check_environment
set "MODE=%~1"
set "SPEC=%WHEEL%"
set "SPECNAME="
for %%W in ("%WHEEL%") do set "SPECNAME=%%~nxW"
if not "%MODE%"=="none" set "SPEC=%WHEEL%[%MODE%]"
if not "%MODE%"=="none" set "SPECNAME=%SPECNAME%[%MODE%]"
set "VENV=%WORK%\venv-%MODE%"

echo == Environment '%MODE%': pip install %SPECNAME%
"%PYTHON%" -m venv "%VENV%" || exit /b 1
"%VENV%\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check "%SPEC%" || exit /b 1
"%VENV%\Scripts\python.exe" -m pip check || exit /b 1

rem Run away from the repository so the source tree can never shadow the installed wheel; -I also ignores PYTHON* variables.
pushd "%WORK%"
"%VENV%\Scripts\python.exe" -I "%CHECK%" check-env %MODE% %VERSION%
set "STATUS=%ERRORLEVEL%"
popd
exit /b %STATUS%
