Set-Location $PSScriptRoot

if (Get-Command npm -ErrorAction SilentlyContinue) {
    npm.cmd run start
    exit $LASTEXITCODE
}

if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" "main.py" "start"
    exit $LASTEXITCODE
}

python "main.py" "start"
