# Security Checklist

## Secrets handling

- Never commit `.env` or any file containing credentials.
- Use `.env.example` for non-sensitive defaults only.
- Set DB credentials through environment variables.
- Rotate credentials if they have ever appeared in git history.

## Database hardening

- Use a dedicated runtime user with least required privileges.
- Keep administrative users separate from ingestion users.
- Restrict DB network access to trusted hosts/VPC/private network.
- Enable SSL/TLS for non-local database connections.

## Publication readiness

Before making the repository public:

1. Confirm `git status` has no secret files staged.
2. Search for potential secret patterns:
   - passwords
   - API keys
   - tokens
3. Verify `.gitignore` includes local secret files (`.env*`).
4. Regenerate credentials used during development.
