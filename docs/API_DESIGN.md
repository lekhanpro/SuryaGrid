# API Design - Suryagrid AI Phase 1

## Base URL
`/api/v1`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /auth/login | JWT login |
| POST | /auth/register | User registration |
| GET | /sites | List sites |
| POST | /sites | Create site |
| POST | /predict | Run prediction cycle |
| GET | /dsm/{site_id} | Get DSM results |
| GET | /timeline/{site_id} | Get timeline data |

## Response Format

```json
{
  "success": true,
  "message": "OK",
  "data": {}
}
```
