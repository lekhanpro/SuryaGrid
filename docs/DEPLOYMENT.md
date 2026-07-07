# Deployment — AWS

SuryaGrid is designed to run on AWS with the following architecture:

| Component | Service | Notes |
|-----------|---------|-------|
| Backend API | ECS Fargate (behind ALB) | Containerized FastAPI, auto-healing |
| Database | RDS PostgreSQL 16 | Private subnet, encrypted |
| Cache | ElastiCache Redis 7 | Private subnet |
| Frontend | S3 + CloudFront | Static export, global CDN |
| Container Registry | ECR | Image scanning on push |
| CI/CD | GitHub Actions | OIDC auth, zero stored keys |

## Prerequisites

- AWS account with admin access (or scoped IAM permissions for the resources below)
- [Terraform >= 1.5](https://developer.hashicorp.com/terraform/install) installed locally
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured (`aws configure`)
- Docker (for building container images)
- GitHub repo with Actions enabled

## 1. Provision Infrastructure (Terraform)

```bash
cd infra/terraform

# Copy and fill in your values
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set db_password, backend_image (use "PLACEHOLDER" for first run)

terraform init
terraform plan          # Review what will be created
terraform apply         # ~5-10 min for RDS + NAT
```

Key outputs after apply:
- `ecr_repository_url` — where to push the backend image
- `alb_dns_name` — backend API URL
- `cloudfront_domain` — frontend URL
- `frontend_bucket` — S3 bucket for static files
- `cloudfront_distribution_id` — for cache invalidation

## 2. Push the First Backend Image

```bash
# Get values from terraform output
ECR_URL=$(terraform output -raw ecr_repository_url)
AWS_REGION=ap-south-1

# Authenticate Docker with ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

# Build and push
cd ../../backend
docker build -t $ECR_URL:latest .
docker push $ECR_URL:latest
```

Then update `terraform.tfvars` with the actual image URI and re-apply:
```bash
cd ../infra/terraform
# Set backend_image = "<ecr_url>:latest" in terraform.tfvars
terraform apply
```

## 3. Deploy Frontend to S3

```bash
cd ../../frontend

# Build static export with the ALB URL baked in
NEXT_PUBLIC_API_URL="http://<alb_dns_name>/api/v1" STATIC_EXPORT=true npm run build

# Sync to S3
aws s3 sync out/ s3://$(cd ../infra/terraform && terraform output -raw frontend_bucket)/ --delete

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id $(cd ../infra/terraform && terraform output -raw cloudfront_distribution_id) \
  --paths "/*"
```

## 4. Set Up GitHub Actions CD (Automated)

The workflow (`.github/workflows/deploy-aws.yml`) auto-deploys on every CI-green push to `main`. Setup:

### a) Create an OIDC IAM Role for GitHub Actions

```bash
# Create the OIDC identity provider (one-time)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create the deploy role (replace YOUR_ORG/YOUR_REPO)
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      "StringLike": { "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*" }
    }
  }]
}
EOF

aws iam create-role --role-name suryagrid-github-deploy \
  --assume-role-policy-document file://trust-policy.json
```

Attach permissions (ECR push, ECS deploy, S3 sync, CloudFront invalidate):
```bash
aws iam attach-role-policy --role-name suryagrid-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# Create custom policy for ECS + S3 + CloudFront (see below)
aws iam put-role-policy --role-name suryagrid-github-deploy \
  --policy-name deploy-permissions \
  --policy-document file://deploy-policy.json
```

<details>
<summary>deploy-policy.json</summary>

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::suryagrid-frontend-*",
        "arn:aws:s3:::suryagrid-frontend-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "cloudfront:CreateInvalidation",
      "Resource": "*"
    }
  ]
}
```
</details>

### b) Configure GitHub Repository

Go to **Settings → Secrets and variables → Actions**:

| Type | Name | Value |
|------|------|-------|
| Secret | `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::ACCOUNT_ID:role/suryagrid-github-deploy` |
| Variable | `AWS_REGION` | `ap-south-1` |
| Variable | `ECR_REPOSITORY` | `suryagrid-backend` |
| Variable | `ECS_CLUSTER` | `suryagrid-cluster` |
| Variable | `ECS_SERVICE` | `suryagrid-backend` |
| Variable | `ECS_TASK_FAMILY` | `suryagrid-backend` |
| Variable | `FRONTEND_S3_BUCKET` | *(from terraform output)* |
| Variable | `CLOUDFRONT_DISTRIBUTION_ID` | *(from terraform output)* |
| Variable | `BACKEND_API_URL` | `http://<alb_dns_name>/api/v1` |
| Variable | `ALB_URL` | `http://<alb_dns_name>` |

### c) Trigger a Deploy

Push to `main` (CI passes → deploy triggers), or go to **Actions → Deploy to AWS → Run workflow**.

## 5. Verify

```bash
# Backend health
curl http://<alb_dns_name>/api/v1/health

# Frontend
open https://<cloudfront_domain>

# Logs
aws logs tail /ecs/suryagrid-backend --follow
```

## Cost Estimate (ap-south-1, minimal config)

| Resource | Monthly (~) |
|----------|-------------|
| ECS Fargate (0.5 vCPU, 1GB) | ~$15 |
| RDS db.t4g.micro (20 GB) | ~$13 |
| ElastiCache cache.t4g.micro | ~$12 |
| NAT Gateway + data | ~$35 |
| ALB | ~$18 |
| CloudFront + S3 | ~$1-5 |
| **Total** | **~$95-100/mo** |

To reduce costs: remove NAT Gateway (use VPC endpoints instead), use RDS free tier.

## Production Hardening Checklist

- [ ] Enable HTTPS on ALB (ACM certificate + listener on :443)
- [ ] Set `CORS_ORIGINS` to your actual frontend domain
- [ ] Use AWS Secrets Manager for `db_password` instead of env vars
- [ ] Enable RDS Multi-AZ (`multi_az = true`)
- [ ] Add auto-scaling to ECS service (target tracking on CPU)
- [ ] Set up CloudWatch alarms (5xx rate, ECS task failures, RDS CPU)
- [ ] Enable WAF on ALB for rate limiting / bot protection
- [ ] Uncomment S3 remote backend in `main.tf` for shared state
- [ ] Restrict OIDC trust to `ref:refs/heads/main` for production deploys
