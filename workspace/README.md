# Dedicated harness workspace

This directory is the development-only `WORKSPACE_ROOT` configured in `backend/.env`.

Use a separate, least-privilege workspace in production. The agent must not be configured against `/`, a home directory, or a project containing credentials.
