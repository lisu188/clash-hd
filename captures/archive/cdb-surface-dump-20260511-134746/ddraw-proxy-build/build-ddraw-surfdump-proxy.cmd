@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
cl /nologo /EHsc /LD /W3 /DWIN32 /D_WINDOWS /Fo"C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260511-134746\ddraw-proxy-build\obj\ddraw_surfdump_proxy.obj" /Fe"C:\ClashTests\cdb-castle-barracks-ui\ddraw.dll" "C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp" /link /DEF:"C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\ddraw_surfdump_proxy\ddraw_surfdump_proxy.def" user32.lib gdi32.lib
exit /b %ERRORLEVEL%
