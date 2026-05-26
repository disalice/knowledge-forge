import glob
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import frontmatter
import httpx
from openai import OpenAI

TAGS_FILE = "config/tags.json"

# 60秒でのタイムアウト設定と、SDK標準のリトライ設定
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
    timeout=httpx.Timeout(60.0),
    max_retries=3,
)


def load_all_metadata():
    """全MarkdownファイルからFront Matter（メタデータ）のみを抽出する"""
    metadata_list = []
    for filepath in glob.glob("src/**/*.md", recursive=True):
        if ".vitepress" in filepath or filepath.endswith("index.md"):
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                post = frontmatter.load(f)
                metadata_list.append(
                    {
                        "target_file_path": filepath,
                        "id": post.get("id"),
                        "title": post.get("title", ""),
                        "category": post.get("category", ""),
                    }
                )
        except Exception as e:
            print(f"Warning: Failed to load metadata from {filepath}: {e}")
    return metadata_list


def load_standard_tags():
    """タグのマスターリストを読み込む"""
    if os.path.exists(TAGS_FILE):
        with open(TAGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_standard_tags(tags):
    """タグのマスターリストを更新して保存する"""
    os.makedirs(os.path.dirname(TAGS_FILE), exist_ok=True)
    with open(TAGS_FILE, "w", encoding="utf-8") as f:
        # 重複を排除し、五十音/アルファベット順にソートして保存
        unique_sorted_tags = sorted(list(set(tags)))
        json.dump(unique_sorted_tags, f, ensure_ascii=False, indent=2)


def step1_analyze_and_extract_metadata(issue_body, metadata_list, standard_tags):
    """
    【第1段階】JSONモードを使用し、メタデータとルーティング情報だけを厳格に生成させる
    """
    system_prompt = f"""あなたは優秀なソリューションアーキテクトです。
ユーザーから提案されたIssue内容を分析し、メタデータを決定してください。

【カテゴリの決定ルール】
- ユーザーがIssueフォームの「### カテゴリ (Category)」で選択した値を、
  そのまま厳密に `category` として使用してください。

【タグの決定ルール】
- 現在のタグリスト: {", ".join(standard_tags)}
- 上記のタグから合致するものを優先して選んでください。
- もし既存のタグでは表現できない重要な技術要素や
  新しい概念（例: JWT, Redis, 冪等性 など）が含まれる場合は、
  新しいタグとして作成し、出力に含めてください。

【アクションと対象ファイルパスの決定ルール】
- 既存のナレッジと完全に内容が重複しており、
  既存のファイルを「更新・上書き」すべき場合は、`action="update"` とし、
  `target_file_path` には必ず更新対象となる既存ファイルのパスをそのまま指定してください
- 重複がなく「新規作成」すべき場合は、`action="create"` とし、`target_file_path` に
  `src/{{category}}/{{適切な英単語のファイル名}}.md` を指定してください。

【既存ファイルのメタデータ一覧（重複判定用）】
{json.dumps(metadata_list, ensure_ascii=False, indent=2)}

必ず以下のJSONスキーマのみを出力してください。
{{
  "title": "ナレッジのタイトル（簡潔に）",
  "category": "抽出したカテゴリ名",
  "difficulty": 1から5までの整数（3を標準とする）,
  "tags": ["タグ1", "タグ2", "タグ3", ...],
  "target_artifacts": ["API仕様書", "コード" などの影響成果物],
  "related_file_paths": ["重複・関連する既存ファイルのパス"],
  "action": "create または update",
  "target_file_path": "対象となるファイルパス"
}}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"提案内容:\n{issue_body}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return json.loads(response.choices[0].message.content)


def step2_generate_body_only(issue_body, related_files_content):
    """
    【第2段階】純粋なMarkdownテキストの本文のみをストリーミング生成させる
    """
    system_prompt = f"""あなたは優秀なシニアソフトウェアエンジニアです。
提案されたIssue内容を、プロジェクトに依存しない汎用的なベストプラクティスとして構造化・自動補完してMarkdownを生成してください。

【関連する既存ナレッジの本文】
{related_files_content}

【出力形式の絶対ルール】
1. YAML Front Matter (---で囲まれた部分) は**絶対に含めないでください**。
2. ```markdown のようなコードブロックの装飾は全体に適用しないでください。
3. 以下の見出し構成に統一してください（該当しない項目は削除可）。
   ## 概要
   ## なぜ必要なのか
   ## 実装標準
   ## 設計・実装時のチェックリスト
   ## アンチパターン
   ## 実施・導入によるトレードオフ
   ## 適用範囲と例外
   ## 検証方法
   ## 関連ナレッジ
"""
    try:
        # ストリーミングを有効にしてリクエスト
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"提案内容:\n{issue_body}"},
            ],
            temperature=0.2,
            stream=True,  # ストリーミングによる無通信タイムアウトの防止
        )

        # ストリーミングでチャンクを順次受け取り、結合する
        full_content = ""
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta_content = chunk.choices[0].delta.content
                if delta_content is not None:
                    full_content += delta_content

        # 不要なコードブロック装飾が混入した場合は除去（LLMのブレ対策）
        if full_content.startswith("```markdown"):
            full_content = full_content.replace("```markdown\n", "", 1)
            if full_content.endswith("```"):
                full_content = full_content[:-3]

        # もしLLMが指示を無視してFront Matterを書いた場合の強制除去
        if full_content.startswith("---"):
            parts = full_content.split("---", 2)
            if len(parts) >= 3:
                full_content = parts[2].strip()

        return full_content.strip()

    except Exception as e:
        print(f"Error: {e}")

    raise RuntimeError("Failed to generate markdown body.")


def main():
    issue_body = os.environ.get("ISSUE_BODY", "")
    author = os.environ.get("AUTHOR", "")

    jst = timezone(timedelta(hours=+9), "JST")
    today = datetime.now(jst).strftime("%Y-%m-%d")

    # メタデータのロード
    metadata_list = load_all_metadata()
    standard_tags = load_standard_tags()

    print("Step 1: Extracting metadata and routing...")
    start_step1 = time.time()
    meta_json = step1_analyze_and_extract_metadata(
        issue_body, metadata_list, standard_tags
    )
    print(f"-> [Step1 Done] {time.time() - start_step1:.2f} seconds")

    # 新しいタグの検出とマスターリストの更新
    used_tags = meta_json.get("tags", [])
    new_tags = [t for t in used_tags if t not in standard_tags]

    if new_tags:
        print(f"-> Detected new tags: {new_tags}")
        updated_tags = standard_tags + new_tags
        save_standard_tags(updated_tags)
        print("-> Updated config/tags.json")

    category = meta_json.get("category", "uncategorized")
    action = meta_json.get("action", "create")
    file_path = meta_json.get("target_file_path", f"src/{category}/new_knowledge.md")
    related_paths = meta_json.get("related_file_paths", [])

    print(f"-> Action: {action.upper()}, Category: {category}")

    # 関連ファイルの読み込みと、更新時のID引継ぎ処理
    knowledge_id = str(uuid.uuid4())  # 新規作成時のデフォルトUUID
    related_files_content = ""

    if action == "update" and os.path.exists(file_path):
        with open(file_path, encoding="utf-8") as f:
            post = frontmatter.load(f)
            related_files_content += f"--- File: {file_path} ---\n{post.content}\n\n"
            # 既存ファイルのIDを引き継ぐ
            if post.get("id"):
                knowledge_id = post.get("id")

    for path in related_paths:
        if path != file_path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                related_files_content += f"--- File: {path} ---\n{f.read()}\n\n"

    print("Step 2: Generating markdown body...")
    start_step2 = time.time()
    body_content = step2_generate_body_only(issue_body, related_files_content)
    print(f"-> [Step2 Done] {time.time() - start_step2:.2f} seconds")

    # 最終的な Front Matter の組み立て（Python側で型とフォーマットを強制）
    # JSONの配列データを正しくYAMLリストとして出力するための整形
    tags_str = json.dumps(meta_json.get("tags", []), ensure_ascii=False)
    artifacts_str = json.dumps(
        meta_json.get("target_artifacts", []), ensure_ascii=False
    )

    final_document = f"""---
id: {knowledge_id}
title: {meta_json.get("title", "無題")}
category: {category}
author: {author}
difficulty: {meta_json.get("difficulty", 3)}
tags: {tags_str}
target_artifacts: {artifacts_str}
updated_at: {today}
---

{body_content}
"""

    # ファイルの書き出し
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_document)

    print(f"Successfully processed ({action}) and wrote to {file_path}")


if __name__ == "__main__":
    main()
