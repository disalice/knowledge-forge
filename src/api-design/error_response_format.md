---
id: 23775ace-0942-7e16-3fd7-dc25e61ee999
title: APIエラーレスポンスのフォーマット
category: api-design
author: disalice
difficulty: 中
tags: [API]
target_artifacts: [API設計書, コード]
updated_at: 2026-05-26
---

## 概要

APIのエラーレスポンスのフォーマットをRFC 7807（Problem Details for HTTP APIs）に準拠した統一フォーマット（`application/problem+json`）にすることで、エラー処理を一貫性のあるものにし、フロントエンドや外部クライアントがエラーを容易にハンドリングできるようにします。

## なぜ必要なのか

エラーレスポンスのフォーマットを統一することで、エラーの理由を明確にし、実装のオーバーヘッドとバグを減少させることができます。また、バリデーションエラーなどの複数エラーの返却を標準的な方法で行うことが可能になります。

## 実装標準

エラー発生時には以下のフィールドを含むJSONを返します。

- `type`: エラーの種類を示すURI（ドキュメントへのリンクなど）
- `title`: エラーの概要（人間が読める短い説明）
- `status`: HTTPステータスコード
- `detail`: エラーの詳細な説明
- `instance`: エラーが発生した特定のリクエストURI
- 拡張フィールド: バリデーションエラーの詳細な配列など

## 設計・実装時のチェックリスト

- [ ] エラーレスポンスの `Content-Type` は `application/problem+json` に設定されているか？
- [ ] 必須フィールド（`type`, `title`, `status`）は正しく埋まっているか？
- [ ] バリデーションエラーの場合、どのフィールドがどう間違っているか（`invalid_params`など）が含まれているか？

## アンチパターン

- HTTPステータスコードが `200 OK` を返し、レスポンスボディの中に `{"error": true, "message": "Failed"}` のように含める設計。
- エンドポイントや担当開発者によってエラーレスポンスのJSONのキー（`msg`, `errorMessage`, `details` など）が異なる。

## 実施・導入によるトレードオフ

既存のAPIで独自フォーマットを採用している場合、後方互換性を保つための移行コストがかかる可能性があります。

## 適用範囲と例外

- **スコープ:** クライアントへ公開するすべてのRESTful / HTTP API。
- **例外:** 内部のgRPC通信やGraphQL（これらは独自の標準エラーフォーマットを持っているため）。

## 検証方法

異常系（4xx, 5xx）のテストケースにおいて、レスポンスボディのスキーマがRFC 7807に準拠していることをOpenAPIスキーマ等のバリデータで検証します。

## 関連ナレッジ

- [RFC 7807](https://tex2e.github.io/rfc-translater/html/rfc7807.html)
- [OpenAPI](https://spec.openapis.org/oas/latest.html)の共通Error Schema設計
