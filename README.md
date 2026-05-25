# knowledge-forge

**Engineering Best Practices**

このリポジトリは、ソフトウェアエンジニアリングにおける設計基準やベストプラクティスを一元管理し、洗練させるための個人用ナレッジベースです。GitHub IssueとAI（LLM）を活用し、ナレッジの収集・構造化・ドキュメント化を自動化しています。

人間が読むための静的サイト（VitePress）と、他のLLMエージェントやRAGシステムが読み込むための構造化データ（JSON）の両方を自動で生成・提供します。

## Features

* **AIによるナレッジの自動補完・構造化**: Issueで概要（What）を提案するだけで、AI（GPT-4o mini）が既存のナレッジと照合し、背景（Why）や実装方法（How）を補完して整理されたMarkdownを生成します。
* **人間とAIの協調ワークフロー**: AIが生成したMarkdownは自動でPull Request（PR）として起票され、人間のレビューを経てからメインブランチにマージされます。
* **人間向けドキュメント（VitePress）**: マージされると、人間が読みやすい静的サイトとして[GitHub Pages](https://disalice.github.io/knowledge-forge/)にデプロイされます。
* **LLM向けデータ（JSON）**: 同時に、他のAIシステムがシステムプロンプトやRAGとして活用しやすいJSON形式（Front Matterのメタデータ＋本文）にパースされ、公開されます。

## ワークフロー

ナレッジが提案されてから公開されるまでのサイクルは以下の通りです。

1. **提案 (Issue)**
* 開発者がリポジトリの Issue Forms（ナレッジの追加・更新提案）から、新しいナレッジのカテゴリと概要を入力します。


1. **生成 (GitHub Actions + LLM)**
* Issueの起票/更新をトリガーにワークフローが起動し、`scripts/llm_check.py` が実行されます。
* AIが不足している項目を補完し、重複や矛盾を解決した上でフォーマットを統一したMarkdownを作成し、自動でPRを作成します。


3. **レビュー & マージ (Pull Request)**
* 生成されたPRの内容を人間がレビュー・修正し、`main` ブランチにマージします。


4. **デプロイ (GitHub Pages)**
* `main` ブランチへのプッシュをトリガーに、`scripts/parse_to_json.py` が実行され `dist/llm/` にJSONファイルが生成されます。
* VitePressがビルドされ、人間用のサイト（`dist/human`）とLLM用のJSONがGitHub Pagesへデプロイされます。



## ディレクトリ構成

```text
.
├── .devcontainer/          # Dev Container定義（Node.js + Python/uv）
├── .github/
│   ├── ISSUE_TEMPLATE/     # ナレッジ提案用のIssue Form
│   └── workflows/          # 自動生成・デプロイ用のActions定義
├── dist/
│   ├── human/              # VitePressビルド用の人間向け公開ディレクトリ
│   └── llm/                # LLM/RAG連携用のJSON出力ディレクトリ
├── scripts/
│   ├── llm_check.py        # Issueを元にAIがMarkdownを生成・更新するスクリプト
│   └── parse_to_json.py    # Markdownをメタデータ付きのJSONに変換するスクリプト
└── src/                    # ナレッジのソースとなるMarkdownファイル（SSOT）
    ├── api-design/
    ├── database-design/
    └── ...

```

## 開発の始め方 (Dev Container)

このリポジトリは Dev Container による開発環境を完備しています。ローカルPCに Node.js や Python をインストールする必要はありません。

### 前提条件

* Docker Desktop（または OrbStack 等のコンテナランタイム）
* VS Code または Cursor
* 拡張機能: `Dev Containers` (`ms-vscode-remote.remote-containers`)

### 起動手順

1. 本リポジトリを VS Code / Cursor で開きます。
2. 画面右下に表示される **「コンテナで開く (Reopen in Container)」** をクリックします。（またはコマンドパレットから `Dev Containers: Reopen in Container` を実行）
3. コンテナのビルドが完了すると、自動的に `npm ci` と `uv sync` が実行され、すべての依存関係が準備されます。

### 主要コマンド

コンテナ起動後、VS Code内のターミナルで以下のコマンドが使用可能です。

#### ドキュメントの確認・ビルド (Node.js)

```bash
# ローカルサーバーの起動 (http://localhost:5173/)
npm run docs:dev

# 本番用ビルドの確認
npm run docs:build

```

#### スクリプトの実行・フォーマット (Python)

```bash
# MarkdownからLLM用JSONを手動で生成する
uv run task build-json

# Pythonスクリプトのコード整形とLint
uv run task format
uv run task lint

```