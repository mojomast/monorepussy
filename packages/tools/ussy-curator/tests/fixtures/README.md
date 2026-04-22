---
title: Project Overview
author: Alice
date: 2024-01-15
tags: [api, deployment, docker]
reviewed: 2024-06-01
---

# Project Overview

This document provides an overview of the project architecture.

## API Design

The API follows REST principles. Use `GET /api/v1/users` to fetch users.

## Deployment

Deploy with Docker using the provided `docker-compose.yml`.

```bash
$ docker-compose up -d
```

See also [Setup Guide](setup.md) and [API Reference](api.md).
