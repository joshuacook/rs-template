# Radical Symmetry - Complete Deployment Playbook

This playbook documents both initial setup of new Radical Symmetry projects and ongoing deployment procedures.

## Architecture Overview

- **Pattern**: Gateway + API + AI Service architecture
- **Environments**: Production and Staging (shared data)
- **Platform**: Google Cloud Platform (Cloud Run)
- **CI/CD**: GitHub Actions
- **External Services**: Clerk (auth), OpenAI (AI), Langfuse (tracing)

---

## Part 1: Initial Project Setup

### Prerequisites

- Google Cloud CLI (`gcloud`) installed and authenticated
- GitHub CLI (`gh`) installed and authenticated
- Docker installed
- Node.js/npm installed (for the services)

### Step 1: Create GCP Project

Replace `PROJECT_NAME` with your project name (e.g., rs-template-dev):

```bash
# Create new GCP project  
gcloud projects create PROJECT_NAME --name="PROJECT_NAME"

# Set as active project
gcloud config set project PROJECT_NAME

# Enable billing (replace BILLING_ACCOUNT_ID with your billing account)
# Note: You may need to request billing quota increase if you hit limits
gcloud billing projects link PROJECT_NAME --billing-account=BILLING_ACCOUNT_ID

# If you get "Cloud billing quota exceeded" error:
# 1. Clean up unused projects: gcloud projects delete PROJECT_ID
# 2. Or request quota increase: https://support.google.com/code/contact/billing_quota_increase
# 3. Or try different billing account: gcloud billing accounts list
```

### Step 2: Enable Required GCP APIs

**⚠️ IMPORTANT:** Billing must be enabled before proceeding.

```bash
# Check current billing status
gcloud billing projects describe PROJECT_NAME

# List available billing accounts
gcloud billing accounts list

# Link to billing account (replace with your active billing account ID)
gcloud billing projects link PROJECT_NAME --billing-account=YOUR_BILLING_ACCOUNT_ID

# Enable required APIs (requires billing)
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  containerregistry.googleapis.com
```

### Step 3: Set Up GCP Services

#### Firestore Database
```bash
# Create Firestore database in native mode
gcloud firestore databases create --region=us-central1
```

#### Cloud Storage Bucket
```bash
# Create shared storage bucket
gsutil mb gs://PROJECT_NAME-uploads
```

#### Container Registry
```bash
# Configure Docker for GCR
gcloud auth configure-docker
```

### Step 4: Service Account & IAM Setup

```bash
# Create service account for deployments
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Service Account"

# Grant necessary permissions
for role in roles/run.admin roles/storage.admin roles/secretmanager.admin roles/cloudbuild.builds.builder roles/iam.serviceAccountUser
do
  gcloud projects add-iam-policy-binding PROJECT_NAME \
    --member="serviceAccount:github-actions@PROJECT_NAME.iam.gserviceaccount.com" \
    --role="$role"
done

# Create and download service account key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@PROJECT_NAME.iam.gserviceaccount.com
```

### Step 5: External Services Setup

#### A. OpenAI Setup
1. Go to https://platform.openai.com/api-keys
2. Create new API key (name it "PROJECT_NAME")  
3. Copy the API key (starts with `sk-proj-...`)

#### B. Clerk Setup (Production Instance Required for Mobile)
1. Go to https://clerk.com/ and sign up/sign in
2. Create new application named "PROJECT_NAME"
3. **Important**: Choose "Production" instance (required for mobile development)
4. Configure sign-in methods (email/password, Google, etc.)
5. **Set up custom domain**:
   - Go to "Domains" in Clerk dashboard
   - Add domain: `clerk.PROJECT_NAME.radicalsymmetry.com`
   - **DNS Setup Required**: Add these CNAME records:
     ```
     clerk.PROJECT_NAME.radicalsymmetry.com → frontend-api.clerk.services
     accounts.PROJECT_NAME.radicalsymmetry.com → accounts.clerk.services  
     ```
6. Go to "API Keys" and copy:
   - **Secret Key** (starts with `sk_live_...`)
   - **Publishable Key** (starts with `pk_live_...`)

#### C. Langfuse Setup
1. Go to https://cloud.langfuse.com and sign up/sign in
2. Create new project named "PROJECT_NAME"
3. Go to Settings → API Keys and copy:
   - **Secret Key** (starts with `sk-lf-...`)
   - **Public Key** (starts with `pk-lf-...`)
   - **Host URL**: `https://cloud.langfuse.com`

### Step 6: Integration Testing Setup

#### A. Create Test Bypass Token
```bash
# Generate a secure test bypass token
TEST_TOKEN="test-bypass-token-PROJECT_NAME-$(openssl rand -hex 32)"
echo "Save this token: $TEST_TOKEN"

# Add to GCP Secret Manager
echo -n "$TEST_TOKEN" | gcloud secrets create TEST_BYPASS_TOKEN --data-file=-

# Grant service account access to the secret
gcloud secrets add-iam-policy-binding TEST_BYPASS_TOKEN \
  --member="serviceAccount:github-actions@PROJECT_NAME.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### B. Create Local Development Service Account
```bash
# Create service account for local development
gcloud iam service-accounts create local-development \
  --display-name="Local Development Service Account"

# Grant necessary permissions for local testing
for role in roles/datastore.user roles/storage.objectAdmin roles/secretmanager.secretAccessor
do
  gcloud projects add-iam-policy-binding PROJECT_NAME \
    --member="serviceAccount:local-development@PROJECT_NAME.iam.gserviceaccount.com" \
    --role="$role"
done

# Create and download key for local development
gcloud iam service-accounts keys create local-development-key.json \
  --iam-account=local-development@PROJECT_NAME.iam.gserviceaccount.com

# IMPORTANT: Add local-development-key.json to .gitignore
echo "local-development-key.json" >> .gitignore
```

#### C. Configure Local Environment
Create `.env` file in project root:
```bash
# Project Configuration
GCP_PROJECT_ID=PROJECT_NAME
ENVIRONMENT=development
GOOGLE_APPLICATION_CREDENTIALS=./local-development-key.json

# Test bypass token (copy from step A)
TEST_BYPASS_TOKEN=test-bypass-token-PROJECT_NAME-xxx

# Service URLs for local development
GATEWAY_URL=http://localhost:8080
API_URL=http://localhost:8081
AI_URL=http://localhost:8082

# Model Configuration
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Langfuse Configuration
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_HOST=https://cloud.langfuse.com

# Clerk Configuration
CLERK_SECRET_KEY=your-clerk-secret-key
CLERK_PUBLISHABLE_KEY=your-clerk-publishable-key
CLERK_DOMAIN=https://clerk.PROJECT_NAME.radicalsymmetry.com
CLERK_JWKS_URL=https://clerk.PROJECT_NAME.radicalsymmetry.com/.well-known/jwks.json
```

### Step 7: GitHub Repository Setup

```bash
# Create GitHub repository
gh repo create PROJECT_NAME --public

# Clone and setup
git clone https://github.com/YOUR_USERNAME/PROJECT_NAME.git
cd PROJECT_NAME

# Copy template files from rs-template or create your structure
# ... (copy services, workflows, etc.)

# Add GitHub secrets
gh secret set GCP_SERVICE_ACCOUNT_KEY < github-actions-key.json
gh secret set GCP_PROJECT_ID --body "PROJECT_NAME"
gh secret set GCP_SERVICE_ACCOUNT_EMAIL --body "github-actions@PROJECT_NAME.iam.gserviceaccount.com"

# Add model configuration
gh secret set MODEL_PROVIDER --body "openai"
gh secret set MODEL_NAME --body "gpt-4o-mini"

# Add OpenAI credentials
gh secret set OPENAI_API_KEY --body "your-openai-api-key"

# Add Clerk credentials
gh secret set CLERK_SECRET_KEY --body "your-clerk-secret-key"
gh secret set CLERK_PUBLISHABLE_KEY --body "your-clerk-publishable-key"
gh secret set CLERK_DOMAIN --body "https://clerk.PROJECT_NAME.radicalsymmetry.com"
gh secret set CLERK_JWKS_URL --body "https://clerk.PROJECT_NAME.radicalsymmetry.com/.well-known/jwks.json"

# Add Langfuse credentials
gh secret set LANGFUSE_SECRET_KEY --body "your-langfuse-secret-key"
gh secret set LANGFUSE_PUBLIC_KEY --body "your-langfuse-public-key"
gh secret set LANGFUSE_HOST --body "https://cloud.langfuse.com"

# Add test bypass token (from Step 6A)
gh secret set TEST_BYPASS_TOKEN --body "test-bypass-token-PROJECT_NAME-xxx"
```

---

## Part 2: Ongoing Deployment

### DNS Prerequisites

Ensure these DNS records are configured in your domain provider:

```
*.staging.radicalsymmetry.com -> CNAME -> ghs.googlehosted.com
*.production.radicalsymmetry.com -> CNAME -> ghs.googlehosted.com
```

### Domain Verification
```bash
# Verify domain ownership (one-time setup)
gcloud domains list-user-verified
gcloud domains verify radicalsymmetry.com  # if not already verified
```

### Deployment Process

#### Staging Deployment

1. **Trigger**: Push to `staging` branch
2. **Process**:
   - Build and push Docker images to GCR
   - Deploy services to Cloud Run
   - Map custom domain to gateway service
   - Run integration tests
3. **URL**: `https://{project_id}.staging.radicalsymmetry.com`

#### Production Deployment  

1. **Trigger**: Push to `main` branch
2. **Process**:
   - Build and push Docker images to GCR
   - Deploy services to Cloud Run with production settings
   - Map custom domain to gateway service
   - Verify deployment health
   - Run smoke tests
3. **URL**: `https://{project_id}.production.radicalsymmetry.com`

### Domain Mapping Commands

#### Manual Domain Mapping (if needed)

```bash
# Set project and region first
gcloud config set project {project_id}
gcloud config set run/region us-central1

# Staging (using beta command for region support)
gcloud beta run domain-mappings create \
  --service {project_id}-staging-gateway \
  --domain {project_id}.staging.radicalsymmetry.com \
  --region us-central1

# Production (using beta command for region support)
gcloud beta run domain-mappings create \
  --service {project_id}-production-gateway \
  --domain {project_id}.production.radicalsymmetry.com \
  --region us-central1
```

**Important:** Do NOT add error suppression like `|| echo "already exists"`. Let commands fail loudly so errors can be fixed.

#### Check Domain Mappings

```bash
# List all domain mappings (beta required)
gcloud beta run domain-mappings list --region us-central1

# Describe specific mapping (beta required)
gcloud beta run domain-mappings describe \
  --domain {project_id}.staging.radicalsymmetry.com \
  --region us-central1
```

#### Remove Domain Mapping

```bash
# Delete domain mapping (beta required)
gcloud beta run domain-mappings delete \
  --domain {project_id}.staging.radicalsymmetry.com \
  --region us-central1
```

### Testing

#### Local Testing
```bash
cd tools/test-runner
uv run python run_tests.py local -v
```

#### Staging Testing
```bash
cd tools/test-runner  
uv run python run_tests.py staging -v
```

#### Production Testing
```bash
cd tools/test-runner
uv run python run_tests.py production -v
```

### Troubleshooting

#### Domain Mapping Issues

1. **SSL Certificate Provisioning**: SSL certificates are provisioned automatically but may take 15+ minutes
2. **DNS Propagation**: DNS changes can take up to 48 hours to propagate globally
3. **Domain Verification**: Ensure domain ownership is verified with Google
4. **Command Errors**: Use `gcloud beta run domain-mappings` (not regular `gcloud run domain-mappings`)

#### Check SSL Status
```bash
gcloud beta run domain-mappings describe \
  --domain {project_id}.staging.radicalsymmetry.com \
  --region us-central1 \
  --format="value(status.conditions)"
```

#### Common Issues

- **SSL handshake failures**: SSL certificates take 15+ minutes to provision for new domains
- **503 errors**: Service not ready, wait for SSL provisioning
- **DNS resolution failures**: Check DNS records and propagation  
- **Permission errors**: Verify service account has Cloud Run Admin role
- **First deployment timeout**: Initial domain mapping can take extra time - this is normal
- **"unrecognized arguments: --region"**: Use `gcloud beta run` commands for domain mappings

### Environment Variables

#### Staging
- `ENVIRONMENT=staging`
- `GCP_PROJECT_ID={project_id}`
- Model provider settings (OpenAI/Anthropic/Google)

#### Production  
- `ENVIRONMENT=production`
- `GCP_PROJECT_ID={project_id}`
- Model provider settings (OpenAI/Anthropic/Google)
- Performance settings (higher CPU/memory)

### Monitoring

#### Health Checks
- Staging: `https://{project_id}.staging.radicalsymmetry.com/health`
- Production: `https://{project_id}.production.radicalsymmetry.com/health`

Or use Cloud Run URLs directly (always work immediately):
```bash
# Get Cloud Run URLs
gcloud run services describe {project_id}-staging-gateway --region us-central1 --format="value(status.url)"
gcloud run services describe {project_id}-production-gateway --region us-central1 --format="value(status.url)"
```

#### Logs
```bash
# Gateway logs
gcloud run services logs read {project_id}-staging-gateway --region us-central1

# API logs  
gcloud run services logs read {project_id}-staging-api --region us-central1

# AI logs
gcloud run services logs read {project_id}-staging-ai --region us-central1
```

---

## Projects Reference

| Project | GCP Project ID | GitHub Repo | Domain |
|---------|---------------|------------|---------|
| Template | rs-template-dev | rs-template | rs-template-dev.*.radicalsymmetry.com |
| Muse | rs-muse | rs-muse | muse.radicalsymmetry.com |
| Athena | rs-athena | rs-athena | athena.radicalsymmetry.com |
| Esther | rs-esther | rs-esther | esther.radicalsymmetry.com |
| Zelda | rs-zelda | rs-zelda | zelda.radicalsymmetry.com |

## Cost Optimization

- Use Cloud Run's pay-per-request pricing
- Set up Cloud Run concurrency limits
- Configure automatic scaling based on traffic
- Monitor usage with Cloud Monitoring
- Set up billing alerts

## Security Considerations

- Keep service account keys secure
- Use least-privilege IAM roles
- Enable VPC connector for internal service communication
- Set up Cloud Armor for DDoS protection
- Regular security audits of IAM permissions
- Never commit secrets or `.env` files to Git
- Use Secret Manager for all sensitive values

---

*Last updated: August 2024*