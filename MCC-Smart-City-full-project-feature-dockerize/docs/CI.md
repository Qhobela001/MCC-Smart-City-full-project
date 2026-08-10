# CI: Build & Push Docker images

This repository includes a GitHub Actions workflow that builds the backend and frontend Docker images and pushes them to a container registry.

Workflow location: `.github/workflows/docker-build-push.yml`

How it decides where to push
- If the repository has `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` set in **Repository secrets**, the workflow will push to Docker Hub under that account.
- If those secrets are not set, the workflow pushes to GitHub Container Registry (`ghcr.io/<org-or-user>/...`) using `GITHUB_TOKEN`.

Required (recommended) repository secrets
- `DOCKERHUB_USERNAME` — your Docker Hub username (optional; leave empty to use GHCR)
- `DOCKERHUB_TOKEN` — Docker Hub access token or password (optional)

How to add repository secrets
1. In GitHub, go to the repository -> Settings -> Secrets -> Actions -> New repository secret.
2. Add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` if you want Docker Hub pushes.

Using the images
- Docker Hub image example: `docker pull <username>/mcc-smart-city-backend:latest`
- GHCR image example: `docker pull ghcr.io/<owner>/mcc-smart-city-backend:latest`

Local developer workflow
1. Keep `.env` local (don't commit secrets). Use `.env.example` as template.
2. For local development run:
```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d
```
