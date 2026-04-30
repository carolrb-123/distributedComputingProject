@echo off
REM Get the hostname
for /f "tokens=*" %%i in ('hostname') do set HOSTNAME=%%i

REM Start llama-server with the hostname
.\build\bin\llama-server.exe -m Meta-Llama-3-8B-Instruct-Q4_K_M.gguf --host %HOSTNAME% --port 9999 -ngl 0