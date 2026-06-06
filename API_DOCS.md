# TeamBoard API — Full Reference

Base URL: `http://localhost:8000`

All request and response bodies are JSON. Protected endpoints require a JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Table of Contents

1. [Health Check](#1-health-check)
2. [Register Company](#2-register-company)
3. [Login](#3-login)
4. [Query Knowledge Base](#4-query-knowledge-base)
5. [Admin Usage Summary](#5-admin-usage-summary)

---

## 1. Health Check

Confirms the server is reachable and running. No authentication required.

```
GET /api/health/
```

### Request

No headers or body required.

### Response — `200 OK`

```json
{
  "status": "ok"
}
```

### Notes

- This endpoint always returns `200` as long as the Django process is alive.
- Use it to verify the server is up before running other requests.

---

## 2. Register Company

Creates a new company account. Returns a JWT access token and a unique API key immediately — no separate login step required.

```
POST /api/auth/register/
```

### Request Headers

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |

### Request Body

```json
{
  "username":     "acmecorp",
  "password":     "securepass123",
  "company_name": "Acme Corp",
  "email":        "dev@acmecorp.com"
}
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `username` | string | Yes | Max 150 chars. Must be unique across all users. |
| `password` | string | Yes | Min 8 characters. Write-only — never returned in responses. |
| `company_name` | string | Yes | Max 255 chars. Display name for the company. |
| `email` | string | Yes | Must be a valid email address format. |

### Response — `201 Created`

```json
{
  "username":     "acmecorp",
  "company_name": "Acme Corp",
  "api_key":      "1aRx0V8goQl1skQZdsAAvD3kJ8...",
  "role":         "client",
  "access":       "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

| Field | Description |
|---|---|
| `username` | The username that was registered. |
| `company_name` | The display name provided during registration. |
| `api_key` | A unique 43-character URL-safe token auto-generated for this company. Save this — it is not re-shown. |
| `role` | Always `"client"` on self-registration. Admin accounts are created separately via a management command. |
| `access` | JWT access token. Use this as the Bearer token for all protected endpoints. Valid for **24 hours**. |

### Response — `400 Bad Request`

Returned when validation fails (duplicate username, missing fields, invalid email, short password).

```json
{
  "username": ["A company with this username already exists."]
}
```

```json
{
  "password": ["This password is too short. It must contain at least 8 characters."],
  "email":    ["Enter a valid email address."]
}
```

### How It Works Internally

1. The payload is validated by `RegisterSerializer`.
2. Django's `User.objects.create_user()` creates the user record.
3. A `post_save` signal fires automatically and creates a linked `Company` record with a fresh `api_key` (generated using `secrets.token_urlsafe(32)`).
4. The view then updates `company_name` and returns the response.

---

## 3. Login

Authenticates an existing company and returns a fresh JWT access token.

```
POST /api/auth/login/
```

### Request Headers

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |

### Request Body

```json
{
  "username": "acmecorp",
  "password": "securepass123"
}
```

| Field | Type | Required |
|---|---|---|
| `username` | string | Yes |
| `password` | string | Yes |

### Response — `200 OK`

```json
{
  "access":       "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "username":     "acmecorp",
  "company_name": "Acme Corp",
  "api_key":      "1aRx0V8goQl1skQZdsAAvD3kJ8...",
  "role":         "client"
}
```

| Field | Description |
|---|---|
| `access` | New JWT access token. Valid for **24 hours** from the time of this login. |
| `username` | The authenticated user's username. |
| `company_name` | The company's display name. |
| `api_key` | The company's permanent API key (same value since registration). |
| `role` | Either `"client"` or `"admin"`. |

### Response — `400 Bad Request`

Returned if required fields are missing.

```json
{
  "username": ["This field is required."],
  "password": ["This field is required."]
}
```

### Response — `401 Unauthorized`

Returned if the username does not exist or the password is wrong.

```json
{
  "detail": "Invalid username or password."
}
```

### Notes

- Each login call issues a **new** token. Previous tokens remain valid until they expire (24h).
- The `role` field in the response tells you whether to use the admin endpoints.

---

## 4. Query Knowledge Base

Searches the Knowledge Base for entries matching a keyword. Logs every query automatically.

```
POST /api/kb/query/
```

**Authentication required** — include a valid JWT Bearer token.

### Request Headers

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer <access_token>` |

### Query Parameters (URL)

| Parameter | Type | Default | Max | Description |
|---|---|---|---|---|
| `page` | integer | `1` | — | Page number. Must be ≥ 1. |
| `page_size` | integer | `5` | `20` | Results per page. Capped server-side at 20. |

Example URL with pagination:
```
POST /api/kb/query/?page=2&page_size=3
```

### Request Body

```json
{
  "search": "select_related"
}
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `search` | string | Yes | Max 255 chars. Must not be blank or empty string. |

### Response — `200 OK`

```json
{
  "search":      "select_related",
  "count":       2,
  "page":        1,
  "page_size":   5,
  "total_pages": 1,
  "results": [
    {
      "id":       1,
      "question": "What is select_related in Django ORM?",
      "answer":   "select_related performs a SQL JOIN and fetches related objects in a single query...",
      "category": "database"
    }
  ]
}
```

| Field | Description |
|---|---|
| `search` | The search term that was submitted. |
| `count` | Total number of KB entries matching the search across all pages. |
| `page` | Current page number. |
| `page_size` | Number of results returned on this page. |
| `total_pages` | Total number of pages available. Minimum value is `1` (even when count is 0). |
| `results` | Array of matching KB entries for this page. Empty array `[]` if no matches. |

Each result object:

| Field | Description |
|---|---|
| `id` | Unique identifier of the KB entry. |
| `question` | The question text. |
| `answer` | The full answer text. |
| `category` | One of: `api`, `database`, `cloud`, `framework`, `general`. |

### Response — `200 OK` — No results

When no KB entries match the search term, the API still returns `200` (not `404`). This is correct REST behaviour — the search itself succeeded, it just found nothing.

```json
{
  "search":      "xyzzy_nonexistent_term",
  "count":       0,
  "page":        1,
  "page_size":   5,
  "total_pages": 1,
  "results":     []
}
```

### Response — `400 Bad Request`

Returned when the `search` field is missing or blank.

```json
{
  "search": ["This field may not be blank."]
}
```

```json
{
  "search": ["This field is required."]
}
```

### Response — `401 Unauthorized`

Returned when no token is provided or the token is invalid/expired.

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### How the Search Works

- Performs a **case-insensitive substring match** on both `question` and `answer` fields.
- The SQL condition is effectively: `WHERE question ILIKE '%term%' OR answer ILIKE '%term%'`
- Searching for `"database"` will match an entry whose answer mentions the word "database" anywhere.
- The full result count and a `QueryLog` record are created inside a **single atomic transaction** — so the logged `results_count` always matches the actual query, even under concurrent requests.

### KB Entry Categories

| Category | What it covers |
|---|---|
| `api` | REST APIs, JWT, HTTP, authentication concepts |
| `database` | SQL, Django ORM, transactions, indexing |
| `cloud` | AWS S3, Docker, deployment |
| `framework` | Django internals, DRF, signals, permissions |
| `general` | General software engineering topics |

---

## 5. Admin Usage Summary

Returns aggregated analytics across all companies. Restricted to admin accounts only.

```
GET /api/admin/usage-summary/
```

**Authentication required** — JWT Bearer token with `role = "admin"`.

### Request Headers

| Header | Value |
|---|---|
| `Authorization` | `Bearer <admin_access_token>` |

No request body.

### Response — `200 OK`

```json
{
  "total_queries":    42,
  "active_companies": 3,
  "top_search_terms": [
    { "search_term": "database", "count": 12 },
    { "search_term": "jwt",      "count": 8  },
    { "search_term": "docker",   "count": 5  },
    { "search_term": "select_related", "count": 3 },
    { "search_term": "REST API", "count": 2  }
  ]
}
```

| Field | Description |
|---|---|
| `total_queries` | Total number of KB queries made across all companies since the platform started. |
| `active_companies` | Number of distinct companies that have made at least one query. |
| `top_search_terms` | List of up to **5** most frequently searched terms, ordered by frequency descending. |

Each item in `top_search_terms`:

| Field | Description |
|---|---|
| `search_term` | The exact string that was searched. |
| `count` | How many times this term has been searched across all companies. |

### Response — `401 Unauthorized`

Returned when no token is provided.

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Response — `403 Forbidden`

Returned when a valid token is provided but the company's role is `"client"`.

```json
{
  "detail": "Access restricted to platform administrators."
}
```

### How to Get an Admin Account

Admin accounts cannot be self-registered through the API. They are created using the Django management command:

```bash
docker exec teamboard_web python manage.py create_admin \
  --username admin \
  --password Admin1234! \
  --email admin@example.com \
  --company-name "TeamBoard HQ"
```

Then login normally via `POST /api/auth/login/` to get the admin JWT.

---

## Error Reference

| HTTP Status | When it occurs |
|---|---|
| `200 OK` | Request succeeded. |
| `201 Created` | Resource created successfully (registration). |
| `400 Bad Request` | Invalid or missing input fields. Response body contains field-level error messages. |
| `401 Unauthorized` | No token provided, token is expired, or credentials are wrong. |
| `403 Forbidden` | Valid token but insufficient role (client attempting admin endpoint). |

---

## JWT Token Lifetimes

| Token | Lifetime |
|---|---|
| Access token | 24 hours |
| Refresh token | 7 days (issued internally, not exposed via a route in this API) |

When an access token expires, log in again via `POST /api/auth/login/` to get a new one.

---

## Query Log — What Gets Recorded

Every call to `POST /api/kb/query/` automatically creates a `QueryLog` record in the database with:

- Which company made the query
- The exact search term used
- How many results were found
- The timestamp

This data feeds the `/api/admin/usage-summary/` endpoint. You can inspect it directly in pgAdmin:

```sql
SELECT
  c.company_name,
  ql.search_term,
  ql.results_count,
  ql.queried_at
FROM api_querylog ql
JOIN api_company c ON c.id = ql.company_id
ORDER BY ql.queried_at DESC;
```
