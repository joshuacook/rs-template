# Radical Symmetry Service Template

This template provides the base structure for all Radical Symmetry projects (rs-athena, rs-esther, rs-muse, rs-zelda).

## Architecture

The template follows a 3-service architecture:
- **Gateway Service**: Public-facing authentication and routing
- **API Service**: Core business logic (internal)
- **AI Service**: AI/LLM operations (internal)

## Directory Structure

```
template/
├── services/
│   ├── gateway/       # Auth gateway service
│   ├── api/           # Main API service
│   └── ai/            # AI processing service
├── mobile/            # React Native mobile app
├── .github/
│   └── workflows/     # GitHub Actions CI/CD
└── docs/             # Documentation
```

## Services

### Gateway Service (Port 8080)
- Handles authentication via Clerk
- Routes requests to internal services
- Public-facing endpoint

### API Service (Port 8081)
- Core business logic
- Database operations (Firestore)
- File storage (Cloud Storage)

### AI Service (Port 8082)
- OpenAI integration
- Langfuse tracing
- AI-powered features

## Configuration

Each service uses environment variables for configuration:
- `PROJECT_ID`: GCP project ID
- `ENVIRONMENT`: production/staging/development
- `CLERK_*`: Clerk authentication
- `OPENAI_API_KEY`: OpenAI API key
- `LANGFUSE_*`: Langfuse tracing

## Deployment

The deployment workflow follows this pattern:
- **PR to staging branch** → Runs all tests
- **Merge to staging branch** → Deploys to staging environment
- **Merge to main branch** → Deploys to production environment

## Usage

To use this template for a new project:

1. Copy the template to your project directory
2. Update PROJECT_NAME placeholders with your project name
3. Configure GitHub secrets
4. Push to trigger deployment

## Testing Strategy

**Important**: No GCP services are ever mocked. All tests use real GCP services.

### Unit Tests
- Test business logic only (not external functionality)
- Run in UV environments within each service
- Located in `services/{service}/tests/unit/`
- Run with: `cd services/gateway && uv run pytest tests/unit/`

### Integration Tests
- Test real service interactions with actual GCP services
- Located in `services/{service}/tests/integration/`
- Orchestrated by test runner tool
- Require test bypass token for authentication

### Test Bypass Token
Each project has a test bypass token that allows integration tests to authenticate without Clerk:
- Token name: `TEST_BYPASS_TOKEN_PROJECT_NAME`
- Stored in: GitHub Secrets, GCP Secret Manager, local `.env`
- When used, gateway passes standardized test admin user to internal services
- Services don't know they're being tested - they receive normal user headers

### Running Tests

```bash
# Unit tests for a service
cd services/gateway
uv run pytest tests/unit/

# Integration tests locally (requires docker-compose running)
cd tools/test-runner
python run_tests.py local -v

# Integration tests against staging
python run_tests.py staging -v

# Integration tests against production (use with caution)
python run_tests.py production

# Test specific service only
python run_tests.py local -s gateway
```

## Development

```bash
# Copy .env.example to .env and fill in values
cp .env.example .env

# Run services locally
docker-compose up

# Run individual service
cd services/gateway && python main.py
```