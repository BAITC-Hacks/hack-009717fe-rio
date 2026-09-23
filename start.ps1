$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    & $pythonCommand.Source "$PSScriptRoot/app.py" @args
} else {
    $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledPython) { & $bundledPython "$PSScriptRoot/app.py" @args }
    else { Write-Error 'Install Python 3.10+ and run python app.py.' }
}
