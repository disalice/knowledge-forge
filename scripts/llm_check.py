import glob
import json
import os
import time
from datetime import datetime

import frontmatter
import httpx
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

# 60秒でのタイムアウト設定と、SDK標準のリトライ設定
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
    timeout=httpx.Timeout(60.0),
    max_retries=3,
)


def get_existing_categories():
    """src直下のディレクトリ一覧を取得する（隠しフォルダを除く）"""
    src_dir = "src"
    if not os.path.exists(src_dir):
        return []
    return [
        d
        for d in os.listdir(src_dir)
        if os.path.isdir(os.path.join(src_dir, d)) and not d.startswith(".")
    ]


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
                        "title": post.get("title", ""),
                        "description": post.get("description", ""),
                        "category": post.get("category", ""),
                        "tags": post.get("tags", []),
                    }
                )
        except Exception as e:
            print(f"Warning: Failed to load metadata from {filepath}: {e}")
    return metadata_list


def step1_analyze_issue(issue_body, metadata_list, existing_categories):
    """
    【第1段階】メタデータのみを渡し、カテゴリ・ファイルパス・アクションをJSONで決定する
    ※Markdown本文の生成はここでは行わない
    """
    categories_str = ", ".join(existing_categories) if existing_categories else "なし"

    system_prompt = f"""あなたは優秀なソリューションアーキテクトです。
ユーザーから提案されたIssue内容を分析し、以下の項目を決定してください。

1. カテゴリの決定:
   既存のカテゴリ一覧から選択するか、新規概念の場合はケバブケース
   （例: security-design）で新しいカテゴリ名を作成してください。
2. 重複・関連ファイルの特定:
   既存ファイルのメタデータを確認し、詳細な本文をチェックすべきファイル（最大2つまで）の
   `target_file_path` を選出してください。該当なしなら空配列にしてください。
3. アクションと対象ファイルパス:
   - 完全に内容が重複しており、既存のファイルを「更新」すべき場合は
     action="update" とし、target_file_path にそのファイルのパスを指定してください。
   - 「新規作成」すべき場合は action="create" とし、target_file_path に
     "src/{{決定したカテゴリ}}/{{適切な英単語のファイル名}}.md" を指定してください。

【現在の既存カテゴリ】
{categories_str}

【既存ファイルのメタデータ一覧（本文は含まれません）】
{json.dumps(metadata_list, ensure_ascii=False, indent=2)}

必ず以下のJSONスキーマのみを出力してください。
{{
  "category": "決定したカテゴリ名",
  "related_file_paths": ["詳細をチェックすべき既存ファイルのパス1", "パス2"],
  "action": "create または update",
  "target_file_path": "src/.../....md"
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


def step2_generate_markdown(issue_body, author, category, related_files_content, today):
    """
    【第2段階】純粋なMarkdownテキストのみをストリーミングで生成する
    JSONエスケープのオーバーヘッドを無くし、ストリーミングでタイムアウトを防ぐ
    """
    system_prompt = f"""あなたは優秀なシニアソフトウェアエンジニアです。
提案されたIssue内容を、プロジェクトに依存しない汎用的なベストプラクティスとして構造化・自動補完してMarkdownを生成してください。

【選定されたカテゴリ】
{category}

【関連する既存ナレッジの本文（重複・矛盾チェック用）】
{related_files_content}

【出力形式の絶対ルール】
1. JSONフォーマットや ````markdown ```` のようなコードブロックの装飾は一切行わず、
   **純粋なMarkdownテキストのみ**を出力してください。
2. ファイルの先頭には必ずYAML Front Matter（---で囲まれた領域）を含めてください。
   - 必要なキー:
     - id
     - title
     - category
     - author
     - difficulty
     - tags
     - target_artifacts
     - updated_at
   - categoryには "{category}" を、updated_atには "{today}" を設定してください。
3. 本文は以下の見出し構成に統一してください（該当しない項目は削除可）。
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

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            # ストリーミングを有効にしてリクエスト
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"提案者: {author}\n提案内容:\n{issue_body}",
                    },
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

            return full_content

        except APITimeoutError as e:
            print(f"[Attempt {attempt}/{max_attempts}] Timeout error: {e}")
        except APIConnectionError as e:
            print(f"[Attempt {attempt}/{max_attempts}] Connection error: {e}")
        except RateLimitError as e:
            print("Rate limit exceeded. Aborting.")
            raise e
        except Exception as e:
            print(f"[Attempt {attempt}/{max_attempts}] Unexpected error: {e}")

        if attempt < max_attempts:
            print("Retrying in 5 seconds...")
            time.sleep(5)

    raise RuntimeError("Failed to generate markdown after multiple attempts.")


def main():
    issue_body = os.environ.get("ISSUE_BODY", "")
    author = os.environ.get("AUTHOR", "")
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. メタデータのロード
    metadata_list = load_all_metadata()
    existing_categories = get_existing_categories()

    # 2. 【Step 1】 メタデータのみを使用したルーティングとアクション決定
    print("Analyzing category and routing (Step 1)...")
    start_step1 = time.time()
    analysis_result = step1_analyze_issue(
        issue_body, metadata_list, existing_categories
    )
    print(f"-> [Step1 Done] {time.time() - start_step1:.2f} seconds")

    category = analysis_result.get("category", "uncategorized")
    related_paths = analysis_result.get("related_file_paths", [])
    action = analysis_result.get("action", "create")
    file_path = analysis_result.get(
        "target_file_path", f"src/{category}/new_knowledge.md"
    )

    print(f"-> Action: {action.upper()}")
    print(f"-> Selected Category: {category}")
    print(f"-> Target File: {file_path}")

    # 3. 関連ファイルの読み込み
    related_files_content = ""
    for path in related_paths:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                related_files_content += f"--- File: {path} ---\n{f.read()}\n\n"

    if not related_files_content:
        related_files_content = "（関連する既存ナレッジは検出されませんでした。）"

    # 4. 【Step 2】 ストリーミングによるMarkdown本文の生成
    print("Generating structural knowledge markdown via stream (Step 2)...")
    start_step2 = time.time()
    markdown_content = step2_generate_markdown(
        issue_body, author, category, related_files_content, today
    )
    print(f"-> [Step2 Done] {time.time() - start_step2:.2f} seconds")

    # 5. ファイルの書き出し
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Successfully processed ({action}) and wrote to {file_path}")


if __name__ == "__main__":
    main()
