#!/bin/bash
# Reachy Mini 用ローカル会話バックエンドを起動する
#
# 環境変数で上書き可能:
#   S2S_MODEL_NAME       LLM モデル名（Ollama 上の名前）。デフォルト: gemma4
#   S2S_OLLAMA_BASE_URL  Ollama の OpenAI 互換エンドポイント。デフォルト: http://127.0.0.1:11434/v1
#   S2S_LANGUAGE         会話言語。デフォルト: ja
#   S2S_PORT             待ち受けポート。デフォルト: 8765
set -euo pipefail

cd "$(dirname "$0")/.."

MODEL_NAME="${S2S_MODEL_NAME:-gemma4}"
OLLAMA_BASE_URL="${S2S_OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
LANGUAGE="${S2S_LANGUAGE:-ja}"
PORT="${S2S_PORT:-8765}"

exec .venv/bin/speech-to-speech \
  --mode realtime \
  --stt whisper-mlx \
  --stt_model_name large-v3 \
  --language "$LANGUAGE" \
  --llm_backend chat-completions \
  --model_name "$MODEL_NAME" \
  --responses_api_base_url "$OLLAMA_BASE_URL" \
  --responses_api_api_key dummy \
  --responses_api_reasoning_effort none \
  --responses_api_stream \
  --tts qwen3 \
  --qwen3_tts_language auto \
  --enable_live_transcription \
  --ws_host 0.0.0.0 \
  --ws_port "$PORT"
