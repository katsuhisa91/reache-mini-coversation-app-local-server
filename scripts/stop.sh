#!/bin/bash
# Reachy Mini 用ローカル会話バックエンドを停止する
#
# 環境変数で上書き可能:
#   S2S_PORT  待ち受けポート。デフォルト: 8765
set -euo pipefail

PORT="${S2S_PORT:-8765}"

PIDS=$(lsof -nP -t -iTCP:"$PORT" -sTCP:LISTEN || true)

if [ -z "$PIDS" ]; then
  echo "ポート $PORT で待ち受け中のサーバーは見つかりませんでした。"
  exit 0
fi

echo "サーバーを停止します (PID: $PIDS)"
kill $PIDS

# 終了を待つ（最大 10 秒）。終わらなければ SIGKILL で強制停止する
for _ in $(seq 1 10); do
  if ! kill -0 $PIDS 2>/dev/null; then
    echo "停止しました。"
    exit 0
  fi
  sleep 1
done

echo "終了しないため強制停止します (SIGKILL)"
kill -9 $PIDS
echo "停止しました。"
