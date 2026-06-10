# Dashboard baslatma scripti
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot

Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Dashboard baslatiliyor: http://localhost:8501"
python -m streamlit run dashboard/app.py
