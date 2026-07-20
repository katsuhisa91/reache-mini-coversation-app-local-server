"""speech-to-speech 0.2.11 の Lightning Whisper MLX ハンドラーに MLX ロックを差し込む.

Whisper (MLX) と Qwen3-TTS (MLX) が同時に Metal コマンドバッファへエンコードすると
`failed assertion 'A command encoder is already encoding to this command buffer'`
でプロセスごとクラッシュする。他の MLX ハンドラーが使っているグローバルロック
(speech_to_speech.utils.mlx_lock) を transcribe 呼び出しに適用して直列化する。

冪等: 適用済みならそのまま終了する。
"""

import sys
import sysconfig
from pathlib import Path

# import すると MLX（Metal）の初期化が走るため、パスだけを組み立てて直接編集する
TARGET = (
    Path(sysconfig.get_paths()["purelib"])
    / "speech_to_speech"
    / "STT"
    / "lightning_whisper_mlx_handler.py"
)

IMPORT_OLD = "from speech_to_speech.STT.base_stt_handler import BaseSTTHandler\n"
IMPORT_NEW = (
    "from speech_to_speech.STT.base_stt_handler import BaseSTTHandler\n"
    "from speech_to_speech.utils.mlx_lock import MLXLockContext\n"
)

WARMUP_OLD = """        for _ in range(n_steps):
            _ = self.model.transcribe(dummy_input)["text"].strip()
"""
WARMUP_NEW = """        for _ in range(n_steps):
            with MLXLockContext(handler_name=self.__class__.__name__):
                _ = self.model.transcribe(dummy_input)["text"].strip()
"""

PROCESS_OLD = """        audio = vad_audio.audio
        if self.start_language != "auto":
            transcription_dict = self.model.transcribe(audio, language=self.start_language)
        else:
            transcription_dict = self.model.transcribe(audio)
            language_code = transcription_dict["language"]
            if language_code not in SUPPORTED_LANGUAGES:
                logger.warning(f"Whisper detected unsupported language: {language_code}")
                if self.last_language in SUPPORTED_LANGUAGES:  # reprocess with the last language
                    transcription_dict = self.model.transcribe(audio, language=self.last_language)
                else:
                    transcription_dict = {"text": "", "language": "en"}
            else:
                self.last_language = language_code
"""
PROCESS_NEW = """        audio = vad_audio.audio
        with MLXLockContext(handler_name=self.__class__.__name__):
            if self.start_language != "auto":
                transcription_dict = self.model.transcribe(audio, language=self.start_language)
            else:
                transcription_dict = self.model.transcribe(audio)
                language_code = transcription_dict["language"]
                if language_code not in SUPPORTED_LANGUAGES:
                    logger.warning(f"Whisper detected unsupported language: {language_code}")
                    if self.last_language in SUPPORTED_LANGUAGES:  # reprocess with the last language
                        transcription_dict = self.model.transcribe(audio, language=self.last_language)
                    else:
                        transcription_dict = {"text": "", "language": "en"}
                else:
                    self.last_language = language_code
"""


def main() -> int:
    source = TARGET.read_text()

    if "MLXLockContext" in source:
        print(f"適用済み: {TARGET}")
        return 0

    for old, new, name in [
        (IMPORT_OLD, IMPORT_NEW, "import"),
        (WARMUP_OLD, WARMUP_NEW, "warmup"),
        (PROCESS_OLD, PROCESS_NEW, "process"),
    ]:
        if old not in source:
            print(
                f"error: パッチ対象のコード（{name}）が見つかりません。"
                " speech-to-speech のバージョンが 0.2.11 か確認してください。",
                file=sys.stderr,
            )
            return 1
        source = source.replace(old, new, 1)

    TARGET.write_text(source)
    print(f"パッチ適用完了: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
