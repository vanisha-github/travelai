# AI Travel Planner

A production-ready, multi-agent AI travel planning system powered by **CrewAI** and **Google Gemini**. Instead of a simple chatbot, this project deploys 5 specialized AI agents that collaborate to research destinations, recommend hotels, plan itineraries, estimate budgets, and provide weather-aware travel advice.

---

## Features

- **5 Collaborative AI Agents** — Each agent handles a specific domain (hotels, attractions, weather, budget, planning)
- **Real-time Web Search** — SerpAPI integration for live hotel, attraction, and travel data
- **Weather-Aware Planning** — OpenWeather API integration for climate-based itinerary adjustments
- **Budget Optimization** — Automatic cost breakdowns with money-saving suggestions
- **Personalized Itineraries** — Tailored to traveller preferences, interests, and budget
- **PDF Export** — Download trip itineraries as formatted PDF documents
- **Local Trip Storage** — Save and retrieve previous trip plans
- **Modern UI** — Clean Streamlit interface with interactive cards and expandable panels

---

## Architecture

```
User Input (Streamlit UI)
        │
        ▼
  FastAPI Backend (/plan-trip)
        │
        ▼
  CrewAI Orchestrator
        │
        ├─→ Hotel Agent ──────→ SerpAPI Search
        ├─→ Attraction Agent ─→ SerpAPI Search
        ├─→ Weather Agent ────→ OpenWeather API
        ├─→ Budget Agent ─────→ SerpAPI + Calculations
        │
        ▼
  Travel Planner Agent (compiles final itinerary)
        │
        ▼
  Structured Response → Streamlit UI
```

---

## Folder Structure

```
aitravelnew/
├── backend/
│   ├── agents.py          # 5 CrewAI agent definitions
│   ├── tasks.py           # Task definitions for each agent
│   ├── crew.py            # CrewAI crew orchestration
│   ├── services.py        # Weather and SerpAPI service layers
│   ├── tools.py           # CrewAI tools (search, weather, hotels)
│   ├── config.py          # Environment configuration (Pydantic)
│   ├── models.py          # Pydantic request/response models
│   ├── schemas.py         # Agent output schemas
│   ├── utils.py           # Helper functions and logging
│   └── main.py            # FastAPI application
├── frontend/
│   └── app.py             # Streamlit UI
├── .env.example           # Environment variable template
├── requirements.txt       # Python dependencies
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.12+
- pip or poetry

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-travel-planner.git
   cd ai-travel-planner
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys.

---

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `GOOGLE_API_KEY` | Google Gemini API key | Yes |
| `SERP_API_KEY` | SerpAPI key for web search | Yes |
| `OPENWEATHER_API_KEY` | OpenWeather API key | Optional (falls back to SerpAPI) |
| `GEMINI_MODEL` | Gemini model name | No (default: `gemini-2.0-flash`) |
| `HOST` | Server host | No (default: `0.0.0.0`) |
| `PORT` | Server port | No (default: `8000`) |

---

## Running the Application

### Backend (FastAPI)

```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend (Streamlit)

In a separate terminal:

```bash
cd frontend
streamlit run app.py
```

The UI will open at `http://localhost:8501`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/plan-trip` | Plan a complete trip |
| `GET` | `/weather/{city}` | Get weather for a city |
| `GET` | `/hotels/{destination}` | Search hotels |
| `GET` | `/trips` | List saved trips |

### POST /plan-trip

```json
{
  "source_city": "New York",
  "destination": "Paris",
  "num_days": 5,
  "budget": 3000,
  "num_travellers": 2,
  "interests": ["food", "history", "shopping"],
  "hotel_preference": "standard"
}
```

---

## Screenshots

<!-- Add screenshots here -->
*Coming soon*

---

## Future Improvements

- Interactive destination map with Folium
- Currency conversion integration
- Multi-language support
- Real-time flight price comparison
- User authentication and trip history dashboard
- Support for multi-city itineraries
- Integration with booking APIs

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, CrewAI, Pydantic
- **AI:** Google Gemini 2.5 Flash via CrewAI
- **Search:** SerpAPI for web search, OpenWeather for weather
- **Frontend:** Streamlit
- **PDF:** ReportLab

---

## License

MIT
