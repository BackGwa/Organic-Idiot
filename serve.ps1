Set-Location $PSScriptRoot

$trainer = Start-Process -FilePath "trainer\.venv\Scripts\python.exe" -ArgumentList "trainer\train.py" -NoNewWindow -PassThru

try {
  bun server/index.ts
}
finally {
  Stop-Process -Id $trainer.Id -ErrorAction SilentlyContinue
}
