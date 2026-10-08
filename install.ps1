$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  irm https://astral.sh/uv/install.ps1 | iex
  $env:Path = "$HOME\.local\bin;$env:Path"
}
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
  irm https://bun.sh/install.ps1 | iex
  $env:Path = "$HOME\.bun\bin;$env:Path"
}

uv venv -q --allow-existing trainer\.venv --python 3.12
uv pip install -q --python trainer\.venv -r trainer\requirements.txt --torch-backend auto
bun install --silent --cwd web
bun run --silent --cwd web build --logLevel error
