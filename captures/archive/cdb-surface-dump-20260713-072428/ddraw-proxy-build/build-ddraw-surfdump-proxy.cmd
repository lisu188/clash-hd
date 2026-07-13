@echo off
setlocal
rem Hardened shells set NoDefaultCurrentDirectoryInExePath, which breaks the
rem bare-name vswhere.exe lookup inside vcvars; clear it for this build only.
set NoDefaultCurrentDirectoryInExePath=
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" set "PATH=%PATH%;%ProgramFiles(x86)%\Microsoft Visual Studio\Installer"
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
cl /nologo /EHsc /LD /W3 /DWIN32 /D_WINDOWS /Fo"C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260713-072428\ddraw-proxy-build\obj\ddraw_surfdump_proxy.obj" /Fe"C:\ClashTests\cdb-surface-dump-hdlayout\ddraw.dll" "C:\Users\andrz\git\clash-hd\src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp" /link /DEF:"C:\Users\andrz\git\clash-hd\src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.def" user32.lib gdi32.lib
exit /b %ERRORLEVEL%
