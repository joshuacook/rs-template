# Radical Symmetry Service Template

This template provides the base structure for all Radical Symmetry projects (rs-athena, rs-esther, rs-muse, rs-zelda).

## ✅ Live Deployments

### Production Environment
- **Gateway**: https://rs-template-dev-production-gateway-109961180485.us-central1.run.app
- **Status**: All systems operational

### Staging Environment  
- **Gateway**: https://rs-template-dev-staging-gateway-109961180485.us-central1.run.app
- **Status**: All 7 E2E integration tests passing

## Features Implemented
- ✅ **3-Service Architecture**: Gateway, API, AI services
- ✅ **Authentication**: JWT with Auth0 integration
- ✅ **File Storage**: Cloud Storage with pre-signed URLs
- ✅ **AI Integration**: OpenAI GPT chat functionality
- ✅ **CI/CD Pipeline**: Automated testing and deployment
- ✅ **Service-to-Service Auth**: Google Cloud ID tokens
- ✅ **Integration Testing**: Comprehensive E2E test suite

## Documentation Structure

- **[PROJECT_SPEC.yml](PROJECT_SPEC.yml)** - Complete project specification and configuration
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current deployment and development status
- **[DEPLOYMENT_PLAYBOOK.md](../DEPLOYMENT_PLAYBOOK.md)** - Step-by-step deployment instructions

## Quick Start

### Local Development

```bash
# Copy .env.example to .env and fill in values
cp .env.example .env

# Run services locally with Docker Compose
docker-compose up

# Or run individual service
cd services/gateway && python main.py
```

### Running Tests

```bash
# Unit tests for a service
cd services/gateway && uv run pytest tests/unit/

# All tests summary
make test-summary

# Integration tests (requires Docker Compose running)
cd services/gateway
TEST_BYPASS_TOKEN="your-token" TEST_BASE_URL="http://localhost:8080" \
  uv run pytest tests/integration/ -v
```

### Linting

```bash
# Format code
ruff format services/

# Check linting
ruff check services/
```

## Deployment Workflow

1. **PR to staging** → Runs linting, unit tests, docker build checks
2. **Merge to staging** → Deploys to staging Cloud Run + runs integration tests
3. **PR to main** → Production readiness checks
4. **Merge to main** → Deploys to production Cloud Run

## Using This Template

1. Copy the template to your new project
2. Update `PROJECT_SPEC.yml` with your project details
3. Replace `rs-template-dev` with your GCP project ID
4. Configure GitHub secrets (see PROJECT_SPEC.yml for list)
5. Create staging branch: `git checkout -b staging`
6. Push to trigger deployment workflows

## Project Structure

```
rs-template/
├── services/
│   ├── gateway/       # Auth gateway service (port 8080)
│   ├── api/          # Main API service (port 8081)
│   └── ai/           # AI service (port 8082)
├── tools/
│   ├── test-runner/  # Integration test orchestrator
│   └── check-openai-models.py
├── .github/
│   └── workflows/    # GitHub Actions CI/CD
├── PROJECT_SPEC.yml  # Project specification
├── PROJECT_STATUS.md # Current status
└── docker-compose.yml
```

For detailed information, refer to the documentation files listed above.