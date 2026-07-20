#!/bin/bash
# Reachy Mini ローカル会話バックエンドのセットアップ
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv が見つかりません。https://docs.astral.sh/uv/ を参照してインストールしてください。" >&2
  exit 1
fi

echo "==> Python 3.12 の venv を作成"
uv venv --python 3.12 .venv

echo "==> speech-to-speech をインストール"
uv pip install --python .venv/bin/python "speech-to-speech[whisper-mlx]==0.2.11"

echo "==> Whisper MLX の GPU 競合バグにパッチを適用"
.venv/bin/python scripts/patch_whisper_mlx_lock.py

if command -v ollama >/dev/null 2>&1; then
  if ! ollama list | grep -q "^gemma4"; then
    echo "==> Ollama に gemma4 モデルを取得（約 10GB）"
    ollama pull gemma4
  else
    echo "==> Ollama の gemma4 モデルは取得済み"
  fi
else
  echo "warning: ollama が見つかりません。https://ollama.com/ からインストールして 'ollama pull gemma4' を実行してください。" >&2
fi

echo "==> セットアップ完了。./scripts/run.sh で起動できます。"
