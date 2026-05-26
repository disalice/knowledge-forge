---
id: 1
title: REST APIのレスポンスにおけるrequestIdの必須化
description: REST APIのレスポンスには必ずrequestIdを含めることで、トレーサビリティを向上させることができます。
category: api-design
author: disalice
difficulty: 2
tags: [API, トレーサビリティ]
target_artifacts: [API仕様書, ドキュメント]
updated_at: 2026-05-25
---

### 概要

REST APIのレスポンスには必ずrequestIdを含めることが推奨されます。これにより、リクエストのトレーサビリティが向上し、問題発生時のデバッグが容易になります。また、フロントエンド側での追跡を容易にするために、trace_idも含めるべきです。

### 理由

- トレーサビリティの向上
- 問題発生時のデバッグの容易さ
- フロントエンド側での追跡の容易さ

### 実装例

```json
{
  "requestId": "12345",
  "trace_id": "67890",
  "data": {...}
}
```

### 注意点

- requestIdとtrace_idはユニークである必要があります。
- 各レスポンスに必ず含めるようにしてください。
