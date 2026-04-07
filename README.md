## ShopBuddy

**Team:** Muhammad Arham Hussain Khan, Partham Kumar (GrayCoders)
**Theme & Challenge:** Theme 7 — Open Innovation
**Track:** Open Innovation

### Problem statement

Online shopping decisions are often opaque: users do not know why certain products were selected, filtered out, or ranked higher than others. **ShopBuddy** solves this by providing transparent, step-by-step AI reasoning while comparing products across platforms and normalizing prices across currencies.

### Why multi-agent?

This workflow has multiple specialized tasks that are easier, safer, and more reliable when split across cooperating agents: query understanding, marketplace collection, quality filtering, ranking, review intelligence, and explanation generation. A single agent can answer quickly, but a multi-agent pipeline gives clearer accountability, better explainability, and cleaner separation of concerns.

### Agent architecture

| Agent                                     | Role                                                                                            |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Input Safety Gate Agent                   | Blocks harmful, non-shopping, or prompt-injection style user input before orchestration starts. |
| Query Interpreter Agent (Supervisor)      | Converts user intent into clean search terms, budget, and constraints; starts a search session. |
| Human Approval Checkpoint                 | Pauses for user confirmation of extracted keywords before scraping begins.                      |
| Marketplace Collector Agent (Scraper)     | Fetches products from Daraz and Amazon, maps to a shared schema, and normalizes currency.       |
| Quality Gate Agent (Filter)               | Applies relevance, budget, reviews, and duplicate filters with explicit pass/fail reasons.      |
| Value Ranker Agent (Analyzer)             | Computes value scores and assigns recommendation badges to top candidates.                      |
| Review Analyst Agent (Reviewer)           | Summarizes customer review sentiment, themes, and trust signals for top products.               |
| Explainability Narrator Agent (Explainer) | Generates plain-English transparency reports and per-product recommendation reasoning.          |

**State Graph Visualization:** [workflow_diagram.png](graph_output/workflow_diagram.png)

### How to run

1. Clone the repository.
2. Backend setup:
   - `cd backend`
   - Create `.env` from [backend/.env.example](backend/.env.example)
   - `pip install -r requirements.txt`
   - `uvicorn main:app --reload`
3. Frontend setup:
   - Open a new terminal and run `cd frontend`
   - Create `.env` from [frontend/.env.example](frontend/.env.example)
   - `npm install`
   - `npm run dev`
4. Open the frontend URL shown by Vite (usually `http://localhost:5173`).

### Demo

[[Demo Video Link](https://drive.google.com/drive/folders/1VU_gfrBKLmZngQIfEvx8MrEE9Ux45Imr?usp=sharing)]

### Tech stack

- Languages: Python, JavaScript (React)
- Backend: FastAPI, LangGraph, LangChain, SQLAlchemy
- Frontend: React, Vite, Tailwind CSS, shadcn/magicui components
- Models: Gemini 3 Flash, Llama 3.3 70B (Groq), Llama 3.1 8B (Groq)
- Data Sources: Daraz scraper, Amazon scraper
- APIs: Google GenAI API, Groq API, ExchangeRate-API
- Database: Supabase Postgres
