import glob
import json
import os
from datetime import datetime

import frontmatter
from openai import OpenAI

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
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
    """
    全MarkdownファイルからFront Matter（メタデータ）のみを抽出し、
    軽量なインデックスを作成する
    """
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
    """【第1段階】メタデータのみを渡し、カテゴリ決定と、重複・関連する可能性のあるファイルを特定する"""
    categories_str = ", ".join(existing_categories) if existing_categories else "なし"

    system_prompt = f"""あなたは優秀なソリューションアーキテクトです。
ユーザーから提案されたIssue内容を分析し、以下の2点を決定してください。

1. カテゴリの決定:
   既存のカテゴリ一覧、または既存ファイルのメタデータ一覧を確認し、最も適切なカテゴリを選択してください。
   もし既存カテゴリに該当しない新しい概念の場合は、今後追加されるであろうナレッジの予想をしながら、
   ケバブケース（例: security-design）で新しいカテゴリ名を作成してください。
   無理に2単語にする必要はなく、1単語でも3単語以上でも問題ありません。

2. 重複・関連ファイルの特定:
   既存ファイルのメタデータ（タイトルや概要）を確認し、
   今回の提案内容と「重複」「矛盾」「強い関連性」があり、
   詳細な本文をチェックすべきファイル（最大2つまで）の
   `target_file_path` を選出してください。
   該当がなければ空配列にしてください。

【現在の既存カテゴリ】
{categories_str}

【既存ファイルのメタデータ一覧（本文は含まれません）】
{json.dumps(metadata_list, ensure_ascii=False, indent=2)}

必ず以下のJSONスキーマのみを出力してください。
{{
  "category": "決定したカテゴリ名",
  "related_file_paths": ["詳細をチェックすべき既存ファイルのパス1", "パス2"]
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
    """【第2段階】絞り込まれた特定のファイル本文のみをコンテキストに含め、最終的なMarkdownを生成する"""
    system_prompt = f"""あなたは優秀なシニアソフトウェアエンジニアです。
提案されたIssue内容を、プロジェクトに依存しない汎用的なベストプラクティスとして構造化・自動補完してMarkdownを生成してください。
自動補完の際は、ベストプラクティスに則りなるべく具体的に(数値化できると望ましい)、かつ嘘や虚飾、絵文字の使用をしないようにしてください。
関連ナレッジの項目については、Issue内に含まれていなければ補完せず無いものとして扱ってください。

【選定されたカテゴリ】
{category}

【関連する既存ナレッジの本文（重複・矛盾チェック用）】
{related_files_content}

【ナレッジの構造化と自動補完ルール】
情報が不足している項目がある場合、あなたの持つ一般的な知識を用いて自動補完（推測・加筆）してください。

【判定・編集ルール】
1. 重複がある場合: 既存のMarkdownを統合し、上書きする形で出力。
2. 重複がない場合: 新規Markdownとして出力。
3. Markdown出力フォーマット:
   - YAML Front Matterの以下の要素を含めること
     - id
     - title
     - category
     - author
     - difficulty
     - tags
     - target_artifacts
     - updated_at
   - `category` には選定されたカテゴリ（{category}）を設定すること。
   - `updated_at` には本日付（{today}）を使用すること。
   - 本文は以下の見出し構成に統一。
     - ## 概要
     - ## なぜ必要なのか
     - ## 実装標準
     - ## 設計・実装時のチェックリスト
     - ## アンチパターン
       - なければ削除してOK
     - ## 実施・導入によるトレードオフ
       - なければ削除してOK
     - ## 適用範囲と例外
       - なければ削除してOK
     - ## 検証方法
       - なければ削除してOK
     - ## 関連ナレッジ
       - なければ削除してOK

必ず以下のJSONスキーマのみを出力してください。
{{
  "action": "create" または "update",
  "target_file_path": "src/{category}/ファイル名.md",
  "content": "生成されたMarkdownの全文文字列"
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"提案者: {author}\n提案内容:\n{issue_body}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content)


def main():
    issue_body = os.environ.get("ISSUE_BODY", "")
    author = os.environ.get("AUTHOR", "")
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. 全ファイルの軽量なメタデータのみをロード
    metadata_list = load_all_metadata()
    existing_categories = get_existing_categories()

    # 2. LLMによるカテゴリの決定と関連ファイルの絞り込み
    print("Analyzing category and selecting related files...")
    analysis_result = step1_analyze_issue(
        issue_body, metadata_list, existing_categories
    )
    category = analysis_result["category"]
    related_paths = analysis_result["related_file_paths"]

    print(f"-> Selected Category: {category}")
    print(f"-> Related Files to check: {related_paths}")

    # 3. 指定された関連ファイルのみ、本文をディスクから読み込む
    related_files_content = ""
    for path in related_paths:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                related_files_content += f"--- File: {path} ---\n{f.read()}\n\n"

    if not related_files_content:
        related_files_content = (
            "（関連する既存ナレッジは検出されませんでした。"
            "新規作成として処理してください。）"
        )

    # 4. LLMによる最終的なMarkdownの生成
    print("Generating structural knowledge markdown...")
    final_result = step2_generate_markdown(
        issue_body, author, category, related_files_content, today
    )

    # 5. ファイルの書き出し
    file_path = final_result["target_file_path"]
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_result["content"])

    print(f"Successfully processed ({final_result['action']}) and wrote to {file_path}")


if __name__ == "__main__":
    main()
