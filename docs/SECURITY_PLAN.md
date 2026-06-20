# Security Plan - Suryagrid AI Phase 1

## Authentication
- JWT tokens with HS256 signing
- Token expiration: 60 minutes (configurable)
- Password hashing: bcrypt via passlib

## Authorization (RBAC)
- **admin**: Full access to all sites and settings
- **operator**: Can run predictions, manage own sites
- **viewer**: Read-only access to results

## Rate Limiting
- Redis-backed per-user rate limiting
- Default: 60 requests/minute

## Audit Logging
- All mutations logged with user_id, action, timestamp, IP
- Stored in PostgreSQL audit_log table

## Secrets
- All secrets via environment variables
- Never hardcoded in source
- .env.example provides template (no real values)
