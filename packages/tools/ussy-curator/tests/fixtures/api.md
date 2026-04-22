---
title: API Reference
author: Charlie
date: 2024-03-10
tags: [api, backend, authentication]
---

# API Reference

Detailed reference for all API endpoints.

## Authentication

Use JWT tokens. Call `POST /auth/login` with credentials.

```python
import requests
response = requests.post("/auth/login", json={"user": "admin"})
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/users | List users |
| POST | /api/v1/users | Create user |

See [Project Overview](README.md).
