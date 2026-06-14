# Nomi — AI-Powered Personal Finance Analyzer

> A full-stack financial intelligence dashboard built with Python, Flask, SQL, and Claude AI. Designed to demonstrate end-to-end data analytics capabilities — from raw CSV ingestion to machine learning anomaly detection and AI-generated financial reports.

**[🚀 Live Demo](https://financeiq-92ut.onrender.com)** · **[GitHub](https://github.com/soroushMky)**

---

## Overview

Nomi is a personal finance analytics platform that transforms raw bank transaction data into actionable insights. Built as a portfolio project to demonstrate proficiency in data engineering, machine learning, SQL, and AI integration — the exact skills required for modern data analyst and AI engineering roles.

The app processes a real Kaggle personal finance dataset (617 transactions, 2018–2019) and surfaces patterns, anomalies, and trends through interactive visualizations and an AI coach powered by Anthropic's Claude.

---

## Features

### 📊 Data Analytics
- **Interactive Dashboard** — KPI cards with animated number transitions showing total spend, monthly averages, top categories, and anomaly counts
- **Monthly Trend Analysis** — Line chart detecting a home renovation spike (+82% in May–June 2018)
- **Category Breakdown** — Horizontal bar chart across 18 spending categories
- **Budget vs Actual** — Side-by-side comparison of real spending against planned budgets
- **Year-over-Year Comparison** — Dynamic selector to compare any two years across all metrics

### 🤖 AI & Machine Learning
- **Anomaly Detection** — Isolation Forest ML model flags transactions exceeding 2× category average, filtering out recurring payments
- **AI Financial Coach** — Claude-powered chat interface with full financial context awareness
- **AI Report Generator** — One-click generation of professional financial reports with executive summary, monthly analysis, category insights, and personalized recommendations
- **Financial Health Score** — Composite score (0–100) calculated from spending consistency, budget adherence, anomaly frequency, and goal progress

### 🗄️ SQL & Database
- **Live SQL Insights** — 5 real SQL queries running against SQLite with toggleable code display:
  - Top merchants by total spend (GROUP BY + ORDER BY)
  - Spending by account with averages (GROUP BY + AVG)
  - Biggest single transactions (ORDER BY + LIMIT)
  - Category breakdown with percentages (subquery + calculated fields)
  - Monthly spending comparison (strftime + GROUP BY)
- **Full ORM Layer** — SQLAlchemy models for users, transactions, budgets, goals, and health scores

### 🔐 Authentication & Security
- User registration and login with bcrypt password hashing
- Session-based authentication with Flask-Login
- Per-user data isolation — every query filters by authenticated user ID
- CORS configuration for cross-origin API access

### 📁 Data Pipeline
- CSV upload supporting multiple bank formats (TD Bank, RBC, BMO, Chase, and more)
- Flexible column mapping for inconsistent CSV schemas
- Automated data cleaning — removes credit card payments, paychecks, and non-debit entries
- Real-time ML anomaly detection on upload

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3, Flask, SQLAlchemy |
| **Database** | SQLite (local), configurable for PostgreSQL |
| **Data Processing** | pandas, NumPy |
| **Machine Learning** | scikit-learn (Isolation Forest) |
| **AI Integration** | Anthropic Claude API (claude-sonnet-4-6) |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) |
| **Charts** | Chart.js |
| **Authentication** | Flask-Login, Flask-Bcrypt |
| **Deployment** | Render (backend), GitHub (version control) |
| **Design** | Custom dark UI with particle animation, Inter font |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│   HTML/CSS/JS · Chart.js · Particle Animation   │
└──────────────────┬──────────────────────────────┘
                   │ HTTP / REST API
┌──────────────────▼──────────────────────────────┐
│                Flask Backend                     │
│                                                  │
│  ┌─────────────┐  ┌──────────────┐              │
│  │  Auth API   │  │  Data API    │              │
│  │  /register  │  │  /summary    │              │
│  │  /login     │  │  /monthly    │              │
│  │  /logout    │  │  /categories │              │
│  └─────────────┘  │  /anomalies  │              │
│                   │  /sql-insights│             │
│  ┌─────────────┐  └──────────────┘              │
│  │  AI API     │  ┌──────────────┐              │
│  │  /ai/chat   │  │  ML Pipeline │              │
│  │  /generate- │  │  Isolation   │              │
│  │   report    │  │  Forest      │              │
│  └─────────────┘  └──────────────┘              │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              SQLite Database                     │
│  users · transactions · budgets · goals          │
└─────────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│           Anthropic Claude API                   │
│   AI Coach · Report Generator · Categorizer     │
└─────────────────────────────────────────────────┘
```

---

## Data Pipeline

```
Raw CSV (bank export)
        ↓
pandas ingestion + column mapping
        ↓
Data cleaning (remove non-spending rows)
        ↓
SQLite storage via SQLAlchemy ORM
        ↓
Isolation Forest anomaly detection
        ↓
Health score calculation (5 metrics)
        ↓
REST API endpoints
        ↓
Chart.js visualizations + AI insights
```

---

## Key Technical Decisions

**Why Isolation Forest for anomaly detection?**
Isolation Forest is unsupervised — it requires no labeled training data, which is ideal for personal finance where "normal" varies by user. It isolates anomalies by randomly partitioning the feature space, making it efficient on small datasets.

**Why SQLite instead of PostgreSQL?**
SQLite is zero-configuration and sufficient for single-user financial data. The SQLAlchemy ORM means switching to PostgreSQL for production requires only a one-line config change — demonstrating production-aware architecture thinking.

**Why Flask over Django?**
Flask's minimal footprint gives explicit control over every component — ideal for a portfolio project where understanding the full stack matters more than rapid scaffolding.

**Why Claude over GPT?**
Claude's larger context window allows injecting the full transaction history, monthly totals, and category breakdowns into every AI request — enabling truly personalized financial advice rather than generic responses.

---

## Getting Started

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/soroushMky/financeiq.git
cd financeiq

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate    # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Add your CLAUDE_API_KEY to .env

# Run the app
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

### Using the App
1. Register an account or log in
2. Click **"Use Sample Data"** to load the Kaggle 2018–2019 dataset
3. Explore the dashboard, SQL Insights, Year Comparison, and AI Coach
4. Click **"🤖 Generate AI Report"** for a personalized financial analysis

---

## Project Structure

```
financeiq/
├── app.py                  # Main Flask application + all API routes
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── .env                    # Environment variables (not committed)
├── data/
│   ├── spending_clean.csv  # Cleaned Kaggle transaction data
│   └── Budget.csv          # Monthly budget targets
├── frontend/
│   ├── index.html          # Single-page application
│   ├── app.js              # All frontend logic (~500 lines)
│   └── styles.css          # Dark theme + animations
├── src/
│   ├── models.py           # SQLAlchemy database models
│   └── auth.py             # Authentication blueprint
└── notebooks/
    ├── 01_exploration.ipynb # Data cleaning + EDA
    └── 02_visualizations.ipynb # Chart prototyping
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create new user account |
| POST | `/api/auth/login` | Authenticate user |
| POST | `/api/auth/logout` | End session |
| GET | `/api/summary` | KPI totals + health score |
| GET | `/api/monthly` | Monthly spending by month |
| GET | `/api/categories` | Spending by category |
| GET | `/api/budget` | Actual vs budget comparison |
| GET | `/api/anomalies` | ML-detected anomalies |
| GET | `/api/transactions` | Recent transactions |
| GET | `/api/transactions/all` | Filtered transaction list |
| GET | `/api/sql-insights` | 5 live SQL query results |
| GET | `/api/yearly-comparison` | Year-over-year data |
| POST | `/api/generate-report` | AI financial report |
| POST | `/api/ai/chat` | AI coach conversation |
| POST | `/api/upload` | Upload custom CSV |
| POST | `/api/load-sample` | Load Kaggle sample data |

---

## Dataset

**Source:** [Kaggle Personal Finance Dataset](https://www.kaggle.com/)

- **Raw data:** 806 transactions across 2018–2019
- **After cleaning:** 617 spending transactions
- **Removed:** Credit card payments, paychecks, non-debit entries
- **Categories:** 18 spending categories
- **Accounts:** Checking, Platinum Card, Silver Card
- **Key finding:** Home renovation in May–June 2018 caused an 82% spending spike ($17,200 to Mike's Construction Co.)

---

## What I Learned

- **End-to-end data pipeline** — from raw CSV to cleaned database to API to visualization
- **ML in production** — implementing and deploying Isolation Forest with proper feature engineering
- **AI integration** — prompt engineering with financial context for meaningful, personalized responses
- **SQL at scale** — writing complex queries with subqueries, aggregations, and window-ready patterns
- **Full-stack thinking** — designing APIs that serve both the frontend and potential future integrations
- **UX for data** — making complex financial data readable and actionable for non-technical users

---

## Roadmap

- [ ] AI Transaction Categorizer — auto-categorize uncategorized CSV uploads
- [ ] Spending Forecast — predict next month using time-series analysis
- [ ] PDF Export — downloadable financial reports
- [ ] Light Mode — full design system toggle
- [ ] PostgreSQL migration — production-ready database
- [ ] React frontend — component-based architecture

---

## Author

**Soroush** — UI/UX Designer transitioning into Data Analytics & AI Engineering

- GitHub: [@soroushMky](https://github.com/soroushMky)
- Live Demo: [https://financeiq-92ut.onrender.com](https://financeiq-92ut.onrender.com)

---

## License

MIT License — feel free to use this project as a reference or starting point.

---

*Built with Python, Flask, pandas, scikit-learn, Claude AI, and a lot of coffee ☕*
