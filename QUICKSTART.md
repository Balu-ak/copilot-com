# AutoBrain Quick Start Guide

Get AutoBrain running in under 5 minutes!

## Prerequisites Check

Before starting, make sure you have:
- [ ] Docker Desktop installed and running
- [ ] Git installed
- [ ] At least one LLM API key (OpenAI, Anthropic, or Google)

## 5-Minute Setup

### Step 1: Get the Code (30 seconds)

```bash
# Clone the repository
git clone https://github.com/your-org/autobrain.git
cd autobrain
```

### Step 2: Configure (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Open .env in your editor
nano .env  # or use your preferred editor
```

**Edit these critical lines in .env:**

```bash
# Choose your LLM provider
LLM_PROVIDER=openai

# Add your API key
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

Save and close the file.

### Step 3: Start Services (2 minutes)

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready
# This takes about 30-60 seconds
```

### Step 4: Verify (1 minute)

```bash
# Check all services are running
docker-compose ps

# You should see:
# - autobrain-postgres (healthy)
# - autobrain-redis (healthy)
# - autobrain-weaviate (healthy)
# - autobrain-api (up)
# - autobrain-web (up)
```

### Step 5: Access AutoBrain (30 seconds)

Open your browser and go to:
- **Application**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

That's it! You're ready to use AutoBrain! 🎉

## First Conversation

1. Open http://localhost:3000
2. You'll see the AutoBrain chat interface
3. Try asking: "What is AutoBrain and what can you do?"
4. The AI will respond using your configured LLM provider

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View API logs only
docker-compose logs -f api

# View web logs only
docker-compose logs -f web
```

## Using Make Commands

If you have `make` installed, you can use these shortcuts:

```bash
make init    # First time setup
make up      # Start services
make down    # Stop services
make logs    # View all logs
make status  # Check service health
```

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker info

# Check for port conflicts
lsof -i :3000
lsof -i :8000

# View detailed logs
docker-compose logs
```

### Can't connect to API

1. Make sure all services are healthy: `docker-compose ps`
2. Check API logs: `docker-compose logs api`
3. Verify the API responds: `curl http://localhost:8000/health`

### LLM errors

1. Verify your API key is correct in `.env`
2. Check you have credits/quota with your LLM provider
3. Try a different provider (set `LLM_PROVIDER=anthropic` and add `ANTHROPIC_API_KEY`)

## Next Steps

### Add Document Ingestion

```bash
# Ingest a document
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "demo-org",
    "url": "https://example.com/your-doc",
    "source": "web"
  }'
```

### Enable Slack Integration

1. Create a Slack app
2. Add credentials to `.env`:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_SIGNING_SECRET=your-secret
   ```
3. Restart services: `docker-compose restart`

### Setup Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Production server setup
- Kubernetes deployment
- Cloud provider configuration
- SSL/TLS setup
- Monitoring and backups

## Getting Help

- **Documentation**: Check README.md and DEPLOYMENT.md
- **Logs**: `docker-compose logs -f`
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

## Security Notes

⚠️ **For Development Only**

The default configuration is for development. Before deploying to production:

1. Change all default passwords in `.env`
2. Use strong, unique secrets for `API_SECRET_KEY`
3. Enable authentication (Clerk/Auth.js)
4. Setup SSL/TLS certificates
5. Configure firewall rules
6. Enable audit logging
7. Review [DEPLOYMENT.md](DEPLOYMENT.md) security section

## What's Next?

- ✅ **Done**: Basic setup complete
- 📚 **Learn**: Explore API documentation at http://localhost:8000/docs
- 🔧 **Customize**: Modify agents in `packages/orchestrator/graph.py`
- 🚀 **Deploy**: Follow [DEPLOYMENT.md](DEPLOYMENT.md) for production
- 🤝 **Integrate**: Add Slack, Gmail, Google Drive connectors

Happy building with AutoBrain! 🧠✨
