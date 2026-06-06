# TeamBoard API

A production-ready REST API backend built with **Django 4.2** and **Django REST Framework**. It provides a multi-tenant Knowledge Base (KB) search service with JWT authentication, role-based access control, query logging, and an admin analytics endpoint.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Models](#data-models)
- [API Endpoints](#api-endpoints)
- [Authentication & Authorization](#authentication--authorization)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Run with Docker (recommended)](#run-with-docker-recommended)
  - [Run Locally (without Docker)](#run-locally-without-docker)
- [Management Commands](#management-commands)
- [Testing the API with Postman](#testing-the-api-with-postman)
- [Design Decisions](#design-decisions)

---

## Overview

TeamBoard allows companies to register, authenticate, and search a shared Knowledge Base. Every search is logged per company. An admin role can view aggregated usage analytics across all companies.

Key behaviours:

- Each registered user maps 1-to-1 to a **Company** profile, auto-created via a Django signal.
- A **unique API key** is generated automatically on registration (URL-safe 32-byte token).
- All KB queries are logged atomically — the count is always consistent with the search results.
- The admin analytics endpoint is protected by a custom `IsAdminUser` permission that checks the `Company.role` field (not Django's `is_staff`).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | Django 4.2, Django REST Framework 3.15 |
| Authentication | `djangorestframework-simplejwt` 5.3 (JWT Bearer tokens) |
| Database | PostgreSQL 15 |
| CORS | `django-cors-headers` |
| Server | Gunicorn (production), Django dev server (Docker Compose) |
| Container | Docker + Docker Compose |

---

## Project Structure

```
TeamBoard/
├── api/
│   ├── migrations/          # Database migrations
│   ├── management/
│   │   └── commands/
│   │       ├── create_admin.py   # Creates an admin company user
│   │       └── seed_kb.py        # Seeds 12 sample KB entries
│   ├── admin.py
│   ├── apps.py
│   ├── models.py            # Company, KBEntry, QueryLog
│   ├── permissions.py       # Custom IsAdminUser permission
│   ├── serializers.py       # Input validation + output formatting
│   ├── signals.py           # Auto-creates Company on User save
│   ├── urls.py              # /api/* routes
│   └── views.py             # All view logic
├── teamboard/
│   ├── settings.py          # Django settings (env-driven)
│   ├── urls.py              # Root URL conf
│   └── wsgi.py
├── .env.example             # Environment variable template
├── docker-compose.yml       # Postgres + web service orchestration
├── Dockerfile               # Python 3.11-slim image
├── manage.py
└── requirements.txt
```

---

## Data Models

### `Company`

Extends Django's built-in `User` via a OneToOne relationship. Auto-created by a `post_save` signal when a user is registered.

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOneField → User | CASCADE delete |
| `company_name` | CharField(255) | Set during registration |
| `api_key` | CharField(64), unique | Auto-generated: `secrets.token_urlsafe(32)` |
| `role` | CharField | `'admin'` or `'client'` (default: `'client'`) |
| `created_at` | DateTimeField | Auto set on create |

### `KBEntry`

Stores individual knowledge base Q&A pairs.

| Field | Type | Notes |
|---|---|---|
| `question` | TextField | Full question text |
| `answer` | TextField | Full answer text |
| `category` | CharField | One of: `api`, `database`, `cloud`, `framework`, `general` |
| `created_at` | DateTimeField | Auto set on create |

### `QueryLog`

Immutable audit log of every search performed by a company.

| Field | Type | Notes |
|---|---|---|
| `company` | ForeignKey → Company | CASCADE delete |
| `search_term` | CharField(255) | The search string used |
| `results_count` | PositiveIntegerField | Number of KB entries matched |
| `queried_at` | DateTimeField | Auto set on create |

Indexed on `(company, queried_at)` and `(search_term)` for efficient admin analytics queries.

---

## API Endpoints

Base URL: `http://localhost:8000/api/`

### `GET /api/health/`

Health check. No authentication required.

**Response `200`**
```json
{ "status": "ok" }
```

---

### `POST /api/auth/register/`

Register a new company. No authentication required.

**Request body**
```json
{
  "username":     "acme",
  "password":     "SecurePass1!",
  "email":        "dev@acme.com",
  "company_name": "Acme Corp"
}
```

| Field | Validation |
|---|---|
| `username` | Unique, max 150 chars |
| `password` | Min 8 chars, write-only |
| `email` | Valid email format |
| `company_name` | Max 255 chars |

**Response `201`**
```json
{
  "username":     "acme",
  "company_name": "Acme Corp",
  "api_key":      "KSqrkbORsCX6WRGC6Vx5yc4LWs6mJ5oqLoppZAjw9zo",
  "role":         "client",
  "access":       "<JWT access token>"
}
```

---

### `POST /api/auth/login/`

Authenticate and receive a JWT. No authentication required.

**Request body**
```json
{
  "username": "acme",
  "password": "SecurePass1!"
}
```

**Response `200`**
```json
{
  "access":       "<JWT access token>",
  "username":     "acme",
  "company_name": "Acme Corp",
  "api_key":      "KSqrkbORsCX6WRGC6Vx5yc4LWs6mJ5oqLoppZAjw9zo",
  "role":         "client"
}
```

**Response `401`** — invalid credentials
```json
{ "detail": "Invalid username or password." }
```

---

### `POST /api/kb/query/`

Search the Knowledge Base. **Requires JWT authentication.**

**Query parameters**

| Param | Default | Max | Description |
|---|---|---|---|
| `page` | `1` | — | Page number (1-indexed) |
| `page_size` | `5` | `20` | Results per page |

**Request body**
```json
{ "search": "django transaction" }
```

**Response `200`**
```json
{
  "search":      "django transaction",
  "count":       4,
  "page":        1,
  "page_size":   3,
  "total_pages": 2,
  "results": [
    {
      "id":       2,
      "question": "How does transaction.atomic() work in Django?",
      "answer":   "transaction.atomic() creates a database savepoint...",
      "category": "database"
    }
  ]
}
```

The search performs a **case-insensitive substring match** on both `question` and `answer` fields (`icontains OR`). The query and result count are logged atomically inside a `transaction.atomic()` block.

---

### `GET /api/admin/usage-summary/`

Aggregated usage analytics. **Requires JWT + `admin` role.**

**Response `200`**
```json
{
  "total_queries":    42,
  "active_companies": 5,
  "top_search_terms": [
    { "search_term": "database", "count": 12 },
    { "search_term": "jwt",      "count": 8 }
  ]
}
```

Returns up to 5 top search terms, ordered by frequency descending.

**Response `403`** — authenticated but role is `client`
```json
{ "detail": "Access restricted to platform administrators." }
```

---

## Authentication & Authorization

All endpoints except `/api/health/`, `/api/auth/register/`, and `/api/auth/login/` require a valid JWT in the `Authorization` header:

```
Authorization: Bearer <access token>
```

JWT tokens expire after **24 hours**. Refresh tokens are valid for **7 days** (refresh token endpoint is available via `rest_framework_simplejwt` but not explicitly routed in this project — re-login to get a new access token).

**Role system**

| Role | Who | Access |
|---|---|---|
| `client` | Any registered company | `/api/kb/query/` |
| `admin` | Created via `create_admin` management command | `/api/kb/query/` + `/api/admin/usage-summary/` |

> Note: The `admin` role is independent of Django's built-in `is_staff` / `is_superuser` flags. The custom `IsAdminUser` permission class checks `Company.role` directly.

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recommended)
- Or: Python 3.11+, PostgreSQL 15

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# Django
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
DB_NAME=teamboard
DB_USER=teamboard_user
DB_PASSWORD=teamboard_pass
DB_HOST=db          # use 'localhost' when running without Docker
DB_PORT=5432
```

> In production, set `DEBUG=False`, use a strong random `SECRET_KEY`, and restrict `ALLOWED_HOSTS`.

### Run with Docker (recommended)

```bash
# 1. Build images and start Postgres + Django dev server
docker-compose up --build
```

> Migrations run automatically on container start — the `docker-compose.yml` command is:
> `python manage.py migrate && python manage.py runserver 0.0.0.0:8000`
> You do not need to run `migrate` manually in the Docker workflow.

```bash
# 2. In a separate terminal, seed KB entries and create an admin user
docker exec teamboard_web python manage.py seed_kb
docker exec teamboard_web python manage.py create_admin \
  --username admin \
  --password Admin1234! \
  --email admin@example.com \
  --company-name "My Company"

# API is now live at http://localhost:8000
```

To stop:
```bash
docker-compose down
```

To stop and wipe the database volume:
```bash
docker-compose down -v
```

### Run Locally (without Docker)

Requires a running PostgreSQL instance. Update `DB_HOST=localhost` in `.env`.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Seed data and create admin
python manage.py seed_kb
python manage.py create_admin --username admin --password Admin1234! --company-name "My Company"

# 5. Start the dev server
python manage.py runserver
```

---

## Management Commands

### `create_admin`

Creates a user with `Company.role = 'admin'` in a single step.

```bash
python manage.py create_admin \
  --username <username> \
  --password <password> \
  [--email <email>] \
  [--company-name <name>]
```

Output includes the generated API key:
```
Admin created  →  username: admin  |  api_key: RL8AhIZtY7WeEiEBKRjQmD7XJEC8CXJcRzHkq7r9wDI
```

### `seed_kb`

Inserts 12 sample Knowledge Base entries covering the categories `api`, `database`, `cloud`, and `framework`. The command is **idempotent** — running it multiple times will not create duplicates.

```bash
python manage.py seed_kb
```

---

## Testing the API with Postman

### Quick-start flow

1. **Health check** — `GET http://localhost:8000/api/health/`
2. **Register** — `POST http://localhost:8000/api/auth/register/` with JSON body
3. **Login** — `POST http://localhost:8000/api/auth/login/` → copy the `access` token
4. Set a collection variable `token = <access value>`
5. On all subsequent requests add header: `Authorization: Bearer {{token}}`
6. **Search KB** — `POST http://localhost:8000/api/kb/query/?page=1&page_size=5` with `{"search": "jwt"}`
7. Log in as your admin user, copy that token, and hit `GET http://localhost:8000/api/admin/usage-summary/`

### Suggested Postman environment variables

| Variable | Example value |
|---|---|
| `base_url` | `http://localhost:8000/api` |
| `token` | *(set from login response)* |
| `admin_token` | *(set from admin login response)* |

---

## Design Decisions

**Atomic query logging** — `KBEntry` search and `QueryLog` creation happen inside a single `transaction.atomic()` block. This guarantees `results_count` in the log always matches the actual query at that moment, even under concurrent writes.

**Signal-based Company creation** — Using `post_save` on `User` decouples company setup from the registration view. Any code path that creates a `User` (admin shell, tests, other views) automatically gets a Company profile with a unique API key.

**Custom role permission vs Django's is_staff** — `IsAdminUser` checks `Company.role` rather than `is_staff` because the two systems are intentionally separate. Django's admin site and superuser privileges are unrelated to TeamBoard's client/admin distinction.

**Page-size cap** — `page_size` is capped at 20 server-side to prevent clients from requesting unbounded result sets, regardless of what they send in query params.

**CORS open in development** — `CORS_ALLOW_ALL_ORIGINS = True` is set for local development convenience. In production this should be replaced with an explicit `CORS_ALLOWED_ORIGINS` list.
