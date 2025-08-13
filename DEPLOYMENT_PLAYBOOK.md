# Deployment Playbook

## Overview

This project uses custom domain mapping for staging and production environments:

- **Staging**: `{project_id}.staging.radicalsymmetry.com`
- **Production**: `{project_id}.production.radicalsymmetry.com`

## Prerequisites

### 1. DNS Setup
Ensure the following DNS records are configured in your domain provider:

```
*.staging.radicalsymmetry.com -> CNAME -> ghs.googlehosted.com
*.production.radicalsymmetry.com -> CNAME -> ghs.googlehosted.com
```

### 2. Domain Verification
Verify ownership of the domain with Google:

```bash
# Verify domain ownership (one-time setup)
gcloud domains list-user-verified
gcloud domains verify radicalsymmetry.com  # if not already verified
```

### 3. Required GitHub Secrets
Ensure these secrets are configured in your GitHub repository:

```bash
gh secret set GCP_PROJECT_ID --body "your-project-id"
gh secret set GCP_SERVICE_ACCOUNT_KEY --body "$(cat path/to/service-account-key.json)"
gh secret set MODEL_PROVIDER --body "openai"
gh secret set MODEL_NAME --body "gpt-4o-mini" 
gh secret set OPENAI_API_KEY --body "your-openai-key"
gh secret set TEST_BYPASS_TOKEN --body "your-test-token"
```

## Deployment Process

### Staging Deployment

1. **Trigger**: Push to `staging` branch
2. **Process**:
   - Build and push Docker images to GCR
   - Deploy services to Cloud Run
   - Map custom domain to gateway service
   - Run integration tests

3. **URL**: `https://{project_id}.staging.radicalsymmetry.com`

### Production Deployment  

1. **Trigger**: Push to `main` branch
2. **Process**:
   - Build and push Docker images to GCR
   - Deploy services to Cloud Run with production settings
   - Map custom domain to gateway service
   - Verify deployment health
   - Run smoke tests

3. **URL**: `https://{project_id}.production.radicalsymmetry.com`

## Domain Mapping Commands

### Manual Domain Mapping (if needed)

```bash
# Staging
gcloud run domain-mappings create \
  --service {project_id}-staging-gateway \
  --domain {project_id}.staging.radicalsymmetry.com \
  --region us-central1

# Production  
gcloud run domain-mappings create \
  --service {project_id}-production-gateway \
  --domain {project_id}.production.radicalsymmetry.com \
  --region us-central1
```

### Check Domain Mappings

```bash
# List all domain mappings
gcloud run domain-mappings list --region us-central1

# Describe specific mapping
gcloud run domain-mappings describe {project_id}.staging.radicalsymmetry.com --region us-central1
```

### Remove Domain Mapping

```bash
gcloud run domain-mappings delete {project_id}.staging.radicalsymmetry.com --region us-central1
```

## Testing

### Local Testing
```bash
cd tools/test-runner
uv run python run_tests.py local -v
```

### Staging Testing
```bash
cd tools/test-runner  
uv run python run_tests.py staging -v
```

### Production Testing
```bash
cd tools/test-runner
uv run python run_tests.py production -v
```

## Troubleshooting

### Domain Mapping Issues

1. **SSL Certificate Provisioning**: SSL certificates are provisioned automatically but may take 15+ minutes
2. **DNS Propagation**: DNS changes can take up to 48 hours to propagate globally
3. **Domain Verification**: Ensure domain ownership is verified with Google

### Check SSL Status
```bash
gcloud run domain-mappings describe {project_id}.staging.radicalsymmetry.com \
  --region us-central1 \
  --format="value(status.conditions)"
```

### Common Issues

- **SSL handshake failures**: SSL certificates take 15+ minutes to provision for new domains
- **503 errors**: Service not ready, wait for SSL provisioning
- **DNS resolution failures**: Check DNS records and propagation  
- **Permission errors**: Verify service account has Cloud Run Admin role
- **First deployment timeout**: Initial domain mapping can take extra time - this is normal

## Environment Variables

Each environment requires these variables:

### Staging
- `ENVIRONMENT=staging`
- `GCP_PROJECT_ID={project_id}`
- Model provider settings (OpenAI/Anthropic/Google)

### Production  
- `ENVIRONMENT=production`
- `GCP_PROJECT_ID={project_id}`
- Model provider settings (OpenAI/Anthropic/Google)
- Performance settings (higher CPU/memory)

## Monitoring

### Health Checks
- Staging: `https://{project_id}.staging.radicalsymmetry.com/health`
- Production: `https://{project_id}.production.radicalsymmetry.com/health`

### Logs
```bash
# Gateway logs
gcloud run services logs read {project_id}-staging-gateway --region us-central1

# API logs  
gcloud run services logs read {project_id}-staging-api --region us-central1

# AI logs
gcloud run services logs read {project_id}-staging-ai --region us-central1
```