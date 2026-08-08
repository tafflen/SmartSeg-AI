@echo off
REM Starts all SmartSeg services in PowerShell background jobs; Ctrl+C stops them together.
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$root='%ROOT%'; $python=Join-Path $root '.venv\Scripts\python.exe'; if (!(Test-Path $python)) { Write-Error 'Missing .venv. Follow README Quick Start first.'; exit 1 }; ^
 $jobs=@(); ^
 $jobs += Start-Job -ArgumentList $root,$python -ScriptBlock { param($r,$p) Set-Location (Join-Path $r 'ai-engine'); & $p main.py 2^>^&1 ^| ForEach-Object { '[AI] ' + $_ } }; ^
 $jobs += Start-Job -ArgumentList $root,$python -ScriptBlock { param($r,$p) Set-Location (Join-Path $r 'backend'); & $p -m uvicorn main:app --reload 2^>^&1 ^| ForEach-Object { '[BACKEND] ' + $_ } }; ^
 $jobs += Start-Job -ArgumentList $root -ScriptBlock { param($r) Set-Location (Join-Path $r 'frontend'); npm run dev 2^>^&1 ^| ForEach-Object { '[FRONTEND] ' + $_ } }; ^
 Write-Host 'SmartSeg started. Dashboard: http://localhost:5173  API: http://localhost:8000'; ^
 try { while ($true) { $jobs ^| Receive-Job -Keep; Start-Sleep -Milliseconds 250 } } finally { $jobs ^| Stop-Job -ErrorAction SilentlyContinue; $jobs ^| Remove-Job -Force -ErrorAction SilentlyContinue }"
endlocal
