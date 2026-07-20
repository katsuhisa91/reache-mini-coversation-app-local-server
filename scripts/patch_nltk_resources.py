"""speech-to-speech 0.2.11 の NLTK リソース検索バグを修正する.

s2s_pipeline.py は起動時に品詞タガー averaged_perceptron_tagger_eng を
`tokenizers/` カテゴリで探すが、実体は `taggers/` 配下にインストールされるため
検索は常に失敗し、毎回 nltk.download() が走る。ネットワークが不調だと
インデックス取得に失敗してプロセスごと落ちる（オフライン起動も不可能になる）。

このスクリプトは検索カテゴリを `taggers/` に修正し、あわせて必要な
NLTK リソースを事前ダウンロードして、起動時にネットワークへ出ないようにする。

冪等: 適用済み・ダウンロード済みならそのまま終了する。
"""

import sys
import sysconfig
from pathlib import Path

# import すると MLX（Metal）の初期化が走るため、パスだけを組み立てて直接編集する
TARGET = (
    Path(sysconfig.get_paths()["purelib"])
    / "speech_to_speech"
    / "s2s_pipeline.py"
)

FIND_OLD = 'nltk.data.find("tokenizers/averaged_perceptron_tagger_eng")\n'
FIND_NEW = 'nltk.data.find("taggers/averaged_perceptron_tagger_eng")\n'

RESOURCES = [
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
]


def patch_source() -> int:
    source = TARGET.read_text()

    if FIND_NEW in source:
        print(f"適用済み: {TARGET}")
        return 0

    if FIND_OLD not in source:
        print(
            "error: パッチ対象のコードが見つかりません。"
            " speech-to-speech のバージョンが 0.2.11 か確認してください。",
            file=sys.stderr,
        )
        return 1

    TARGET.write_text(source.replace(FIND_OLD, FIND_NEW, 1))
    print(f"パッチ適用完了: {TARGET}")
    return 0


def ensure_resources() -> int:
    import nltk

    for find_path, download_id in RESOURCES:
        try:
            nltk.data.find(find_path)
            print(f"NLTK リソース取得済み: {find_path}")
        except LookupError:
            print(f"NLTK リソースをダウンロード: {download_id}")
            if not nltk.download(download_id):
                print(f"error: {download_id} のダウンロードに失敗しました。", file=sys.stderr)
                return 1
    return 0


def main() -> int:
    status = patch_source()
    if status != 0:
        return status
    return ensure_resources()


if __name__ == "__main__":
    sys.exit(main())
