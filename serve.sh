#!/usr/bin/env bash
cd "$(dirname "$0")"
export PATH="$HOME/.bun/bin:$PATH"

trainer/.venv/bin/python trainer/train.py &
trainer_pid=$!
trap 'kill "$trainer_pid" 2>/dev/null' EXIT

bun server/index.ts
