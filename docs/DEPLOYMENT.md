# CI/CD & Deployment

This project uses two GitHub Actions workflows: **CI** for validation on every
change and **CD** (GitHub Pages) for publishing the frontend only after CI passes.

## CI — `.github/workflows/ci.yml`

Runs on every push and pull request to `main`. Three jobs run in parallel so
failures surface early:

| Job | What it does |
|-----|--------------|
| Lint & format | `ruff check` and `ruff format --check` on the backend |
| Backend tests | `pytest tests/` (offline, deterministic — no network) |
| Frontend build | `npm ci` + `next build`, then validates `out/index.html` exists |

Dependencies are cached (pip + npm) for faster runs. Config is in
`backend/pyproject.toml` (`[tool.ruff]`).

Run the same checks locally:

```bash
cd backend
ruff check app tests
ruff format --check app tests
python -m pytest tests/ -q

cd ../frontend
npm run build
```

## CD — `.github/workflows/deploy.yml`

Publishes the static frontend to GitHub Pages.

- **Trigger**: runs automatically when the **CI** workflow completes
  **successfully** on `main` (`workflow_run`), or manually via
  **workflow_dispatch**. Deployment never runs on a red build.
- **No hosting assumptions**: `actions/configure-pages` detects the correct base
  path from the repository's actual Pages configuration and passes it to the
  Next.js build via `PAGES_BASE_PATH` (empty for custom-domain/user sites,
  `/<repo>` for project sites). `next.config.js` applies it only when set.
- **Prerequisite validation**: if Pages is not enabled, the workflow stops with a
  clear, actionable error instead of failing obscurely.
- **Artifact validation**: the build fails fast if the static export is missing
  `out/index.html`.
- **Post-deployment verification**: after publishing, the workflow curls the live
  `page_url` and fails if it does not return HTTP 200.

### Enabling Pages (one-time)

Settings → Pages → Build and deployment → Source: **GitHub Actions**. Then push to
`main` (or run the workflow manually).

### Local static export

```bash
cd frontend
npm run build      # produces ./out
npx serve out      # preview at http://localhost:3000
```

The live dashboard fetches the backend API client-side; set
`NEXT_PUBLIC_API_URL` to point at a running backend.
