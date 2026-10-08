#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v bun >/dev/null; then
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
fi

uv venv -q --allow-existing trainer/.venv --python 3.12
uv pip install -q --python trainer/.venv -r trainer/requirements.txt --torch-backend auto
bun install --silent --cwd web
bun run --silent --cwd web build --logLevel error
