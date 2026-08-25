# Publishing `.env` to secure storage

This repository includes a workflow that can generate a `.env` file from repository secrets and upload it to a secure S3 bucket. Use this to provide deployable environment files to your deployment systems without committing secrets to the repository.

Workflow: `.github/workflows/publish-env.yml`

Required repository secrets
- `AWS_ACCESS_KEY_ID` — IAM key with PutObject access to the target S3 bucket
- `AWS_SECRET_ACCESS_KEY` — IAM secret
- `AWS_REGION` — AWS region of the S3 bucket
- `S3_BUCKET` — bucket name where the `.env` will be uploaded

Secret values copied into the `.env`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `BACKEND_PORT`, `FRONTEND_PORT`
- `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ALLOWED_ORIGINS`
- `SUPERADMIN_NAME`, `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`

How it uploads
- The workflow writes a `.env` file using the above secrets and uploads it to:
  `s3://<S3_BUCKET>/envs/<branch>/.env` (private, server-side encrypted)

How to retrieve the file
1. Configure AWS CLI with credentials that have `s3:GetObject` permission.
2. Download the file for `main` branch, for example:

```bash
aws s3 cp s3://<S3_BUCKET>/envs/main/.env ./deploy.env
```

Security notes
- Keep `S3_BUCKET` and AWS credentials restricted to only the workflows and deployers that need them.
- Prefer short-lived credentials and least privilege IAM roles where possible.
