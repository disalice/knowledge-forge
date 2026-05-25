import glob
import json
import os

import frontmatter

SRC_DIR = "src"
DIST_LLM_DIR = "dist/llm"


def convert_md_to_json():
    os.makedirs(DIST_LLM_DIR, exist_ok=True)
    knowledge_list = []

    # src配下のすべてのMarkdownファイルを検索
    for filepath in glob.glob(f"{SRC_DIR}/**/*.md", recursive=True):
        with open(filepath, encoding="utf-8") as f:
            post = frontmatter.load(f)

            # メタデータと本文を分離してJSONオブジェクト化
            knowledge_item = {"metadata": post.metadata, "body": post.content}
            knowledge_list.append(knowledge_item)

            # 個別ファイルの出力（カテゴリごとのディレクトリ構造を維持）
            rel_path = os.path.relpath(filepath, SRC_DIR)
            json_path = os.path.join(DIST_LLM_DIR, rel_path.replace(".md", ".json"))
            os.makedirs(os.path.dirname(json_path), exist_ok=True)

            with open(json_path, "w", encoding="utf-8") as out_f:
                # default=str
                #   dateオブジェクトなどjsonにパースできないオブジェクトを
                #   自動的にstrへ変換
                json.dump(
                    knowledge_item, out_f, ensure_ascii=False, indent=2, default=str
                )

    # 全体インデックス用JSONの出力（LLMが一括で読み込む用）
    with open(
        os.path.join(DIST_LLM_DIR, "index.json"), "w", encoding="utf-8"
    ) as index_f:
        # default=str
        #   dateオブジェクトなどjsonにパースできないオブジェクトを
        #   自動的にstrへ変換
        json.dump(knowledge_list, index_f, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    convert_md_to_json()
    print(f"Successfully converted Markdown to JSON in {DIST_LLM_DIR}")
