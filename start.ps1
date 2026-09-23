$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    & $pythonCommand.Source "$PSScriptRoot/app.py"
} else {
    $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledPython) { & $bundledPython "$PSScriptRoot/app.py" }
    else { Write-Error 'Установите Python 3.10+ и выполните python app.py.' }
}
