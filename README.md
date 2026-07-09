# TradeMind AI 🚀
### Enterprise-Grade AI-Powered Algorithmic Trading & Stock Analysis Platform

[![CI/CD](https://github.com/your-org/trademind-ai/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-org/trademind-ai/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

TradeMind AI is a production-ready, cloud-native fintech platform combining AI-powered stock prediction, portfolio optimization, risk management, and real-time market intelligence for retail investors.

**Live Demo:** https://trademind.ai  
**API Docs:** https://api.trademind.ai/docs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Python 3.12, SQLAlchemy, Celery |
| Database | PostgreSQL 16, Redis 7 |
| AI/ML | TensorFlow, PyTorch, scikit-learn, HuggingFace Transformers |
| Cloud | AWS EC2, RDS, ElastiCache, S3 |
| DevOps | Docker, Kubernetes, GitHub Actions, Terraform |
| Monitoring | Prometheus, Grafana |

---

## Features

- **AI Prediction Center** — LSTM-powered stock forecasting with confidence scores
- **Portfolio Optimizer** — Mean-variance optimization, Sharpe ratio maximization, Monte Carlo simulation
- **Risk Management** — VaR, volatility analysis, drawdown tracking, stop-loss recommendations
- **Live Market Data** — Real-time prices via WebSockets, candlestick charts, RSI/MACD/Bollinger Bands
- **AI Financial Assistant** — GPT-4 powered chatbot with persistent conversation memory
- **News Intelligence** — Sentiment analysis on 50+ financial news sources
- **Paper Trading Simulator** — Virtual trading with $100K virtual balance
- **PWA Support** — Installable app, offline mode, push notifications

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.12+

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/trademind-ai.git
cd trademind-ai
cp .env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Edit `backend/.env` with your API keys.

### 2. Start with Docker Compose

```bash
docker-compose up -d
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090

### 3. Seed Demo Data

```bash
docker-compose exec backend python seed.py
```

Demo accounts:
- **Admin:** admin@trademind.ai / Admin@123
- **Demo:** demo@trademind.ai / Demo@123

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # fill in your keys

# Start PostgreSQL & Redis (or use Docker)
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Seed database
python seed.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

---

## Project Structure

```
trademind-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints
│   │   │   ├── auth.py      # JWT authentication
│   │   │   ├── market.py    # Stock data & quotes
│   │   │   ├── predictions.py # AI predictions
│   │   │   ├── portfolio.py # Portfolio management
│   │   │   ├── watchlist.py # Watchlist CRUD
│   │   │   ├── trading.py   # Paper trading
│   │   │   ├── assistant.py # AI chatbot
│   │   │   ├── news.py      # News & sentiment
│   │   │   ├── risk.py      # Risk analysis
│   │   │   └── admin.py     # Admin panel
│   │   ├── core/
│   │   │   ├── config.py    # Settings
│   │   │   ├── database.py  # SQLAlchemy async
│   │   │   ├── security.py  # JWT & bcrypt
│   │   │   ├── redis.py     # Cache layer
│   │   │   └── deps.py      # DI dependencies
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   │   ├── market_service.py
│   │   │   ├── prediction_service.py
│   │   │   ├── portfolio_service.py
│   │   │   ├── risk_service.py
│   │   │   ├── ai_service.py
│   │   │   └── news_service.py
│   │   ├── tasks/           # Celery background jobs
│   │   └── middleware/      # Logging, rate limiting
│   ├── alembic/             # DB migrations
│   ├── tests/               # Pytest test suite
│   └── seed.py              # Demo data seeder
│
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── (auth)/      # Login, Register pages
│       │   └── (dashboard)/ # All dashboard pages
│       ├── components/
│       │   ├── charts/      # PriceChart, IndicatorsPanel
│       │   ├── dashboard/   # Sidebar, TopBar, MobileNav
│       │   └── ui/          # Reusable UI components
│       ├── store/           # Zustand state management
│       ├── lib/             # API client, utilities
│       └── hooks/           # Custom React hooks
│
├── ai-models/
│   ├── lstm/                # LSTM stock predictor
│   ├── sentiment/           # FinBERT sentiment analyzer
│   ├── portfolio/           # Portfolio optimizer
│   └── risk/                # Risk prediction model
│
├── infrastructure/
│   ├── nginx/               # Reverse proxy config
│   ├── terraform/           # AWS infrastructure as code
│   ├── k8s/                 # Kubernetes manifests
│   └── prometheus.yml       # Monitoring config
│
├── .github/workflows/       # CI/CD pipelines
└── docker-compose.yml       # Local development stack
```

---

## API Documentation

Full OpenAPI docs available at `/docs` (Swagger UI) and `/redoc`.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| GET | `/api/v1/market/quote/{symbol}` | Live stock quote |
| GET | `/api/v1/market/history/{symbol}` | Price history |
| GET | `/api/v1/predictions/{symbol}` | AI prediction |
| POST | `/api/v1/portfolio/optimize` | Portfolio optimization |
| GET | `/api/v1/risk/{symbol}` | Risk analysis |
| POST | `/api/v1/assistant/chat` | AI chat |
| GET | `/api/v1/news/` | Financial news |
| WS | `/ws/market/{symbol}` | Real-time price stream |

---

## Database Schema

```sql
users           -- User accounts, OAuth, roles
prediction_history -- AI prediction records
portfolio       -- User stock holdings
watchlist       -- Tracked symbols
trade_history   -- Paper trading records
ai_chat_history -- Persistent AI conversations
notifications   -- User alerts
paper_trading   -- Virtual trading accounts
```

---

## Deployment

### Frontend → Vercel

```bash
cd frontend
npx vercel --prod
```

### Backend → AWS EC2

```bash
# Provision infrastructure
cd infrastructure/terraform
terraform init
terraform apply -var="db_password=YourSecurePassword"

# Deploy via Docker
ssh ubuntu@<EC2_IP>
git clone https://github.com/your-org/trademind-ai.git
cd trademind-ai && docker-compose up -d
```

### Kubernetes

```bash
kubectl apply -f infrastructure/k8s/
```

---

## Environment Variables

See `.env.example` for all required variables. Key ones:

```env
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
JWT_SECRET=<min 32 chars>
OPENAI_API_KEY=sk-...
ALPHA_VANTAGE_KEY=...
NEWS_API_KEY=...
```

---

## Testing

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm test

# E2E (Playwright)
cd frontend && npx playwright test
```

---

## Security

- JWT authentication with refresh tokens
- bcrypt password hashing (cost factor 12)
- HTTPS enforced via NGINX
- CORS protection
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via React's built-in escaping
- Rate limiting via slowapi
- Secure HTTP headers via NGINX
- Role-based access control (user/admin)

---

## License

MIT License — see [LICENSE](LICENSE)

---

Built with ❤️ by the TradeMind AI Team
