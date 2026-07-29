param(
    [string]$Model = "qwen3-coder:30b",
    [string]$FilePath = "teste.md",
    [string]$Content = "MAURICIO FARIAS DA SILVA"
)

$prompt = @"
Please output only the exact content below, with no extra text or formatting:
$Content
"@

Write-Host "Running Ollama model '$Model' to generate file content..."
$result = ollama run $Model $prompt

if ($LASTEXITCODE -ne 0) {
    Write-Error "Ollama failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Set-Content -Path $FilePath -Value $result -NoNewline
Write-Host "File created: $FilePath"
