# Reachy Mini Conversation App — Local Server (日本語音声会話)

[Reachy Mini](https://huggingface.co/blog/reachy-mini) の公式会話アプリ
[reachy_mini_conversation_app](https://github.com/pollen-robotics/reachy_mini_conversation_app)
を、クラウドではなく **手元の Mac だけ** で動かすためのローカルバックエンドのセットアップです。

Runs the Reachy Mini conversation backend fully locally on a Mac (Apple Silicon):
Whisper (STT) + Ollama Gemma 4 (LLM) + Qwen3-TTS, served as an OpenAI Realtime-compatible
WebSocket that the Reachy Mini app connects to. Tuned for Japanese conversation.

## 仕組み

会話アプリの「Local」接続モードは、`ws://<host>:8765/v1/realtime` に
**OpenAI Realtime 互換の WebSocket サーバー** があることを期待しています。
その実装として Hugging Face の [speech-to-speech](https://github.com/huggingface/speech-to-speech)
（VAD → STT → LLM → TTS のパイプライン）を使い、各コンポーネントを日本語向け・ローカル動作向けに構成します。

```
Reachy Mini（会話アプリ）
   │  ws://<MacのIP>:8765/v1/realtime
   ▼
speech-to-speech サーバー（このリポジトリでセットアップ）
   ├── VAD: Silero VAD
   ├── STT: Whisper large-v3（MLX / 日本語対応）
   ├── LLM: Gemma 4（Ollama 経由, thinking 無効化で低遅延）
   └── TTS: Qwen3-TTS 1.7B（MLX 6bit / 多言語）
```

ポイント:

- デフォルト構成の STT（Parakeet TDT）は欧州 25 言語のみで **日本語非対応** のため、Whisper large-v3 に差し替えています。
- Gemma 4 は思考（reasoning）付きモデルなので、音声会話の遅延を抑えるため `reasoning_effort none` で thinking を無効化しています。
- LLM は Ollama の OpenAI 互換 API（`/v1/chat/completions`）経由なので、Ollama にあるモデルなら差し替え可能です。

## 動作要件

- Apple Silicon の Mac（M1 Pro / 32GB で動作確認）
- [Ollama](https://ollama.com/)（`gemma4` モデルを使用、約 10GB）
- [uv](https://docs.astral.sh/uv/)
- Python 3.12（uv が自動で用意します）
- Reachy Mini と Mac が同じ Wi-Fi ネットワークにいること

## セットアップ

```bash
git clone https://github.com/katsuhisa91/reache-mini-coversation-app-local-server.git
cd reache-mini-coversation-app-local-server
./scripts/setup.sh
```

`setup.sh` は次を行います:

1. `.venv` を作成し `speech-to-speech`（+ Whisper MLX）をインストール
2. 既知の GPU 競合バグへのパッチ適用（後述の「既知の問題」参照）
3. Ollama に `gemma4` モデルがなければ `ollama pull gemma4`

## 起動

```bash
./scripts/run.sh
```

初回起動時は Whisper large-v3 と Qwen3-TTS のダウンロード（数 GB）が走るため数分かかります。
`Uvicorn running on http://0.0.0.0:8765` が出たら準備完了です。

LLM モデルを変えたい場合は環境変数で指定できます:

```bash
S2S_MODEL_NAME=qwen3:8b ./scripts/run.sh
```

## Reachy Mini アプリ側の設定

1. Mac の IP アドレスを調べる: `ipconfig getifaddr en0`
2. 会話アプリの Settings → **Connection** で:
   - HUGGING FACE CONNECTION: **Local**
   - HOST/IP: **Mac の IP アドレス**（例: `192.168.x.x`）
   - PORT: **8765**
3. **Save connection** を押して話しかける

> [!IMPORTANT]
> 会話アプリは Reachy Mini 本体上で動いているため、HOST/IP を `localhost` にすると
> ロボット自身を指してしまい接続できません。必ず Mac の LAN IP を指定してください。

> [!TIP]
> - macOS のファイアウォールが Python への着信許可を求めてきたら「許可」してください。
> - Mac の IP は DHCP で変わることがあります。つながらなくなったら IP を確認し直すか、
>   ルーターで IP を固定してください。SSH リバーストンネル
>   （`ssh -N -R 8765:127.0.0.1:8765 <robot-user>@<robot-host>`）を使えば
>   ロボット側の設定を `localhost` のままにできます。

## 応答速度の目安（M1 Pro）

| 段階 | 時間 |
|------|------|
| LLM（gemma4, thinking 無効）応答開始 | 約 2〜3 秒 |
| TTS 音声の出だし | 0.6〜1.3 秒 |
| 話し終わり → 返事が始まるまで | 3〜4 秒程度 |

会話の間が 5 分以上あくと Ollama がモデルをメモリから解放するため、
次の 1 ターン目だけ応答に数十秒かかることがあります。

## カメラ（ビジョン）

会話アプリの `camera` ツール →Realtime API の `input_image` → Chat Completions の
`image_url` → Ollama という経路がすべて繋がっているため、gemma4 のようなビジョン対応
モデルなら「いま何が見えてる？」といった問いかけに画像を見て答えられます。

## 既知の問題とパッチ

speech-to-speech 0.2.11 の Lightning Whisper MLX ハンドラーは、MLX モデル同士の
Metal（GPU）アクセスを直列化するグローバルロック（`utils/mlx_lock.py`）を通らずに
推論を実行します。このため割り込みの多い会話で Whisper と Qwen3-TTS が同時に GPU に
アクセスすると、次のアサーションでプロセスごと落ちることがあります:

```
failed assertion `A command encoder is already encoding to this command buffer'
```

`scripts/patch_whisper_mlx_lock.py` がインストール済みのハンドラーに
`MLXLockContext` を差し込んで直列化します（`setup.sh` から自動適用、冪等）。

## 恒久的に動かす（任意）

ログイン時に自動起動したい場合は launchd を使います。`scripts/run.sh` を
フルパスで指定した plist を `~/Library/LaunchAgents` に置いてください。

## 関連リンク

- [reachy_mini_conversation_app](https://github.com/pollen-robotics/reachy_mini_conversation_app) — Reachy Mini 公式会話アプリ
- [huggingface/speech-to-speech](https://github.com/huggingface/speech-to-speech) — 音声パイプライン本体
- [Local Reachy Mini conversation（HF blog）](https://huggingface.co/blog/local-reachy-mini-conversation)
