# AutoBrain - Autonomous Knowledge Assistant for Teams

A production-grade AI-powered knowledge assistant that learns from your company docs, email, and Slack; answers questions; summarizes updates; and performs delegated tasks.

## 🚀 Features

- **RAG (Retrieval Augmented Generation)** over enterprise sources
- **Multi-agent orchestration** with LangGraph
- **Chat interface** for natural language queries
- **Document ingestion** from multiple sources
- **Agentic delegation** for automated tasks
- **Enterprise-grade security** with org-scoped access control

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Next.js    │────▶│   FastAPI    │────▶│  PostgreSQL   │
│  Frontend   │     │   Backend    │     │   Database    │
└─────────────┘     └──────┬───────┘     └───────────────┘
                           │
                    ┌──────▼───────┐     ┌───────────────┐
                    │  LangGraph   │────▶│   Weaviate    │
                    │ Orchestrator │     │  Vector DB    │
                    └──────────────┘     └───────────────┘
```

## 📦 Tech Stack

- **Frontend:** Next.js 14 (App Router) + Tailwind CSS
- **Backend:** FastAPI (Python 3.11) + PostgreSQL
- **LLM:** OpenAI GPT / Anthropic Claude / Google Gemini
- **Vector DB:** Weaviate (self-hosted)
- **Orchestration:** LangGraph for multi-agent workflows
- **Infrastructure:** Docker + Docker Compose

## 📋 Prerequisites

- Docker & Docker Compose (20.10+)
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)
- At least one LLM API key (OpenAI, Anthropic, or Google)

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
cd autobrain
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and add your API keys:

```bash
# Minimum required configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start the Stack

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Access the Application

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Weaviate:** http://localhost:8080

## 🔧 Development Setup

### Backend Development

```bash
cd apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --port 8000
```

### Frontend Development

```bash
cd apps/web

# Install dependencies
npm install

# Run development server
npm run dev
```

## 📚 Project Structure

```
autobrain/
├── apps/
│   ├── api/              # FastAPI backend
│   │   ├── main.py       # Main application
│   │   └── requirements.txt
│   └── web/              # Next.js frontend
│       ├── app/          # App router pages
│       ├── package.json
│       └── tailwind.config.js
├── packages/
│   └── orchestrator/     # LangGraph agents
│       └── graph.py      # Multi-agent workflow
├── infra/
│   └── docker/           # Docker configurations
│       ├── Dockerfile.api
│       └── Dockerfile.web
├── scripts/
│   └── init-db.sql       # Database schema
├── docker-compose.yml    # Development stack
└── .env.example          # Environment template
```

## 🔐 Security Features

- **Organization-scoped access control**
- **Row-level security on PostgreSQL**
- **JWT-based authentication (ready for Clerk/Auth.js)**
- **Audit logging for all tool invocations**
- **Secrets management via environment variables**

## 📊 API Endpoints

### Chat & Conversations

- `POST /chat/query` - Send a query and get an answer
- `POST /chat/stream` - Stream responses via SSE
- `GET /conversations/{id}` - Get conversation history

### Document Ingestion

- `POST /ingest/url` - Ingest content from URL
- `GET /documents/{id}` - Get document status

### Actions

- `POST /actions/summarize-weekly` - Schedule weekly summaries

### Health & Auth

- `GET /health` - Health check
- `POST /auth/verify` - Verify authentication

## 🧪 Testing

```bash
# Backend tests
cd apps/api
pytest

# Frontend tests
cd apps/web
npm test
```

## 🚢 Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production deployment instructions including:

- Kubernetes deployment
- Cloud provider setup (AWS EKS, GCP GKE)
- CI/CD with GitHub Actions
- Monitoring and observability
- Scaling considerations

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key |
| `LLM_PROVIDER` | Yes | `openai`, `anthropic`, or `google` |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `WEAVIATE_URL` | Yes | Weaviate URL |

*At least one LLM provider key is required

## 🐛 Troubleshooting

### Services not starting

```bash
# Check logs
docker-compose logs api
docker-compose logs web

# Restart services
docker-compose restart
```

### Database connection issues

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres
```

### Missing API key errors

Make sure your `.env` file has the required API keys and restart:

```bash
docker-compose down
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Weaviate](https://weaviate.io/)
- [OpenAI](https://openai.com/)
- [Anthropic](https://anthropic.com/)

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation
- Review existing issues

---

**AutoBrain** - Empowering teams with autonomous AI assistance
