import glob
import json
import os
import shutil

import frontmatter

SRC_DIR = "src"
DIST_LLM_DIR = "dist/llm"
CONFIG_TAGS_FILE = "config/tags.json"


def convert_md_to_json():
    # 生成前に既存のディレクトリを完全に削除してクリーンアップ
    if os.path.exists(DIST_LLM_DIR):
        shutil.rmtree(DIST_LLM_DIR)

    os.makedirs(DIST_LLM_DIR, exist_ok=True)
    knowledge_list = []

    # 1. src配下のすべてのMarkdownファイルを検索してJSON化
    for filepath in glob.glob(f"{SRC_DIR}/**/*.md", recursive=True):
        # index.md や .vitepress ディレクトリ内は除外
        if ".vitepress" in filepath or filepath.endswith("index.md"):
            continue

        with open(filepath, encoding="utf-8") as f:
            post = frontmatter.load(f)

            # メタデータと本文を分離してJSONオブジェクト化
            knowledge_item = {"metadata": post.metadata, "body": post.content}
            knowledge_list.append(knowledge_item)

            # 個別ファイルの出力（カテゴリごとのディレクトリ構造を維持）
            rel_path = os.path.relpath(filepath, SRC_DIR)
            base_path, _ = os.path.splitext(rel_path)
            json_path = os.path.join(DIST_LLM_DIR, base_path + ".json")
            os.makedirs(os.path.dirname(json_path), exist_ok=True)

            with open(json_path, "w", encoding="utf-8") as out_f:
                # default=str でdateオブジェクトなどのパースエラーを防止
                json.dump(
                    knowledge_item, out_f, ensure_ascii=False, indent=2, default=str
                )

    # 2. 全体インデックス用JSONの出力（LLMが一括で読み込む用）
    with open(
        os.path.join(DIST_LLM_DIR, "index.json"), "w", encoding="utf-8"
    ) as index_f:
        json.dump(knowledge_list, index_f, ensure_ascii=False, indent=2, default=str)

    # 3. タグのマスターリストを dist/llm/tags.json としてコピー・公開
    if os.path.exists(CONFIG_TAGS_FILE):
        dest_tags_path = os.path.join(DIST_LLM_DIR, "tags.json")
        shutil.copy(CONFIG_TAGS_FILE, dest_tags_path)
        print(f"Successfully exposed tags master to {dest_tags_path}")
    else:
        # 万が一マスターが存在しない場合は空配列を出力
        with open(
            os.path.join(DIST_LLM_DIR, "tags.json"), "w", encoding="utf-8"
        ) as tags_f:
            json.dump([], tags_f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    convert_md_to_json()
    print(f"Successfully converted Markdown to JSON in {DIST_LLM_DIR}")
