# project3-url-shortener

A fully serverless URL shortener built on AWS — no servers, no EC2, no maintenance. Paste a long URL, get a short code back, share it anywhere. All infrastructure provisioned with **Terraform** and deployed via **GitHub Actions CI/CD**.

## Live Demo

```bash
# Shorten a URL
curl -X POST "https://zc1uhiv5y9.execute-api.ap-south-1.amazonaws.com/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/Ketanj20"}'

# Response
{
  "short_code": "guOazk",
  "short_url": "https://zc1uhiv5y9.execute-api.ap-south-1.amazonaws.com/guOazk",
  "original_url": "https://github.com/Ketanj20"
}

# Visit the short URL in browser → 301 redirect to original
```

---

## Architecture

```
Client
  │
  │  POST /shorten  {"url": "https://..."}
  ▼
API Gateway (HTTP API)
  │
  │  AWS_PROXY integration
  ▼
Lambda (Python 3.12)
  │
  ├── Generate 6-char alphanumeric code
  ├── Store short_code → original_url in DynamoDB
  └── Return short URL to client

Client visits short URL
  │
  │  GET /{code}
  ▼
API Gateway
  │
  ▼
Lambda
  │
  ├── Look up code in DynamoDB
  ├── Increment hit counter
  └── Return 301 redirect → original URL
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud | AWS (ap-south-1 / Mumbai) |
| Compute | AWS Lambda (Python 3.12) |
| API | AWS API Gateway HTTP API (v2) |
| Database | AWS DynamoDB (PAY_PER_REQUEST) |
| Infrastructure as Code | Terraform |
| CI/CD | GitHub Actions |
| Auth (CI → AWS) | OIDC federation (no static keys) |
| Logs | CloudWatch Logs |

---

## Project Structure

```
project3-url-shortener/
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI/CD — packages and deploys Lambda on push
├── lambda/
│   └── handler.py            # URL shortener logic (shorten + redirect)
└── infra/
    ├── backend.tf             # Remote state (S3 + DynamoDB locking)
    ├── provider.tf
    ├── variables.tf
    ├── dynamodb.tf            # URLs table with TTL
    ├── lambda.tf              # Lambda function + IAM role + packaging
    ├── api_gateway.tf         # HTTP API + routes + CloudWatch logging
    ├── oidc.tf                # GitHub Actions OIDC IAM role
    └── outputs.tf             # API URL, endpoints, resource names
```

---

## API Reference

### POST /shorten
Shorten a URL.

**Request:**
```json
{
  "url": "https://example.com/very/long/url"
}
```

**Response (201):**
```json
{
  "short_code": "aB3xYz",
  "short_url": "https://<api-id>.execute-api.ap-south-1.amazonaws.com/aB3xYz",
  "original_url": "https://example.com/very/long/url"
}
```

### GET /{code}
Redirects to the original URL with a `301` status code. Also increments the hit counter in DynamoDB.

**Response:** `301 Redirect` → original URL

**Error (404):**
```json
{ "error": "Short code aB3xYz not found" }
```

---

## Key Design Decisions

**Serverless — zero servers to manage**
Lambda + API Gateway + DynamoDB means no EC2 instances, no patching, no capacity planning. The whole stack scales automatically from 0 to millions of requests.

**PAY_PER_REQUEST DynamoDB billing**
No provisioned capacity to manage — DynamoDB scales read/write capacity automatically and charges only for what's used. Free tier covers 25GB storage and 200M requests/month.

**Collision-safe code generation**
Uses a conditional write (`ConditionExpression='attribute_not_exists(short_code)'`) to prevent overwriting an existing short code. Retries up to 5 times with a new code on collision — same pattern used in production URL shorteners.

**Hit counter with atomic increments**
Each redirect atomically increments a `hits` counter using DynamoDB's `UpdateExpression` — no race conditions even under concurrent traffic.

**TTL for automatic cleanup**
DynamoDB TTL attribute `expires_at` auto-deletes old entries after 90 days — keeps the table clean without any cron jobs or Lambda cleanup functions.

**OIDC instead of static AWS keys in CI**
GitHub Actions authenticates to AWS via OpenID Connect — no long-lived access keys stored anywhere. The IAM role trust policy is scoped to exactly this repo (`Ketanj20/project3-url-shortener`).

**Least-privilege IAM**
The Lambda execution role only has `dynamodb:GetItem`, `dynamodb:PutItem`, and `dynamodb:UpdateItem` on the specific URLs table ARN — not broad DynamoDB access. The GitHub Actions role only has `lambda:UpdateFunctionCode` — nothing else.

---

## How to Deploy

### Prerequisites
- AWS CLI configured
- Terraform >= 1.7.0

### 1. Apply Terraform

```bash
cd infra
terraform init
terraform apply
```

### 2. Get the API URL

```bash
terraform output shorten_endpoint
```

### 3. Add GitHub repo variable

Go to **Settings → Secrets and variables → Actions → Variables** and add:

| Name | Value |
|---|---|
| `AWS_ROLE_ARN` | output of `terraform output github_actions_role_arn` |

### 4. Push to main — CI deploys Lambda automatically

Any push to `main` packages the Lambda code and deploys it via `aws lambda update-function-code`.

### 5. Test it

```bash
# Shorten
curl -X POST "<api-url>/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Redirect (paste in browser or curl -L)
curl -L "<api-url>/<short-code>"
```

---

## Cost

| Resource | Free Tier | Cost after free tier |
|---|---|---|
| Lambda | 1M requests/month | $0.20 per 1M requests |
| API Gateway | 1M calls/month | $1.00 per 1M calls |
| DynamoDB | 25GB + 200M requests | $1.25 per 1M writes |
| CloudWatch Logs | 5GB/month | $0.50/GB |
| **Total** | **$0 within free tier** 

> This project stays within AWS Free Tier for normal usage. No NAT Gateway, no EC2 — nothing expensive running 24/7.

---

