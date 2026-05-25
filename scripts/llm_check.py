import os
import json
import re
import glob
from datetime import datetime
from openai import OpenAI

# GitHub Modelsのエンドポイントとトークン設定
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
)

def build_system_prompt(existing_files_content):
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""あなたは優秀なシニアソフトウェアエンジニアです。
ユーザーから新しいナレッジ（Issue内容）が提案されます。
あなたのタスクは、既存のナレッジベース（以下）と提案を比較し、以下の処理を行うことです。

【既存のナレッジ】
{existing_files_content}

【判定・編集ルール】
1. 重複・矛盾の確認: 提案内容が既存ナレッジと重複、または矛盾していないか確認してください。
2. 命名規則・表記揺れの自動補正: JSONのキー名、変数名、技術用語において、キャメルケース（例: requestId）とスネークケース（例: trace_id）の混在など表記揺れを検出した場合、システム全体で一貫性が出るように自動でフォーマットを統一してください。
3. 処理の決定:
   - 重複がある場合: 既存のMarkdownを統合し、表記揺れを修正・上書きする形で出力。
   - 重複がない場合: 新規Markdownとして出力。
4. 出力フォーマット:
   - YAML Front Matterを含めた完全なMarkdownを出力すること。
   - 指定されたスキーマ（id, title, category, author, difficulty, tags, target_artifacts, updated_at）を厳守すること。
   - `updated_at` には本日付（{today}）を使用してください。

必ず以下のJSONスキーマのみを出力してください（Markdownのコードブロックは不要です）。
{{
  "action": "create" または "update",
  "target_file_path": "src/カテゴリ名/ファイル名.md",
  "content": "生成されたMarkdownの全文文字列"
}}
"""

def extract_category(issue_body):
    """
    Issue Formsから生成されたMarkdownボディからカテゴリを抽出する。
    例: ### カテゴリ (ディレクトリ)\n\napi-design
    """
    match = re.search(r'### カテゴリ \(ディレクトリ\)\s+([^\n\r]+)', issue_body)
    if match:
        return match.group(1).strip()
    return "unknown-category"

def read_existing_knowledge(category):
    """
    指定されたカテゴリ（ディレクトリ）内の既存Markdownファイルをすべて読み込む。
    """
    category_dir = os.path.join("src", category)
    existing_texts = []
    
    if os.path.exists(category_dir):
        for filepath in glob.glob(f"{category_dir}/**/*.md", recursive=True):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                existing_texts.append(f"--- File: {filepath} ---\n{content}\n")
                
    if not existing_texts:
        return "（現在、このカテゴリに既存のナレッジはありません。これが最初のナレッジになります。）"
        
    return "\n".join(existing_texts)

def main():
    issue_body = os.environ.get("ISSUE_BODY", "")
    author = os.environ.get("AUTHOR", "")
    
    # 1. Issue本文からカテゴリを特定
    category = extract_category(issue_body)
    print(f"Detected category: {category}")
    
    # 2. 対象ディレクトリの既存ナレッジを読み込み
    existing_content = read_existing_knowledge(category)
    
    # 3. LLM APIの呼び出し
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": build_system_prompt(existing_content)},
            {"role": "user", "content": f"提案者: {author}\n提案内容:\n{issue_body}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.2 # 決定論的な出力を促すため低めに設定
    )

    result = json.loads(response.choices[0].message.content)
    
    # 4. ファイルの書き出し処理
    file_path = result["target_file_path"]
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(result["content"])
    print(f"Successfully processed ({result['action']}) and wrote to {file_path}")

if __name__ == "__main__":
    main()