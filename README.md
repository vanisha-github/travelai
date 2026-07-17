# AI Travel Planner

A multi-agent AI travel planning system powered by **CrewAI** and **Google Gemini**. Five specialized AI agents collaborate to research destinations, recommend hotels, plan day-by-day itineraries, estimate budgets, and provide weather-aware travel advice — all served through a FastAPI backend with a rich Streamlit frontend.

---

## Features

- **5 Collaborative AI Agents** — Hotel, Attraction, Weather, Budget, and Travel Planner agents working together via CrewAI
- **Real-time Web Search** — SerpAPI integration for live hotel, attraction, restaurant, and travel data
- **Weather-Aware Planning** — OpenWeather API with forecast enrichment for rain probability, sunrise/sunset, wind, humidity, and UV data
- **Smart Trip Scoring** — 100-point scoring algorithm across 5 weighted categories (Hotels, Attractions, Budget Fit, Weather, Itinerary Quality) with animated ring chart and category breakdown
- **Google Maps Integration** — Every hotel, attraction, and restaurant link opens directly in Google Maps with correct query formatting
- **Budget Optimization** — Pie chart breakdowns (Hotel, Food, Transport, Activities, Misc) with per-person costs, remaining balance, and money-saving suggestions
- **12-Tab Results Dashboard** — Overview, Hotels, Attractions, Day-by-Day Itinerary, Weather, Budget, Food & Restaurants, Transport, Travel Tips, Packing Checklist, AI Insights, and PDF Export
- **Premium Weather UI** — Glassmorphism hero card with animated icons, 5 detail cards, 3 extra data cards, and dynamic context-aware travel tips
- **PDF Export** — Download a formatted travel brochure via ReportLab with colored section bars, clickable links, and all trip data
- **User Session & Trip Storage** — Name-based session system with SQLite database for saving, loading, and deleting trips
- **Fully Responsive Design** — Mobile-first CSS with 3 breakpoints (1024px, 768px, 480px), floating hamburger menu for sidebar, and touch-friendly 44px targets
- **HTML Sanitization** — All AI-generated content is stripped of HTML tags and validated before rendering to prevent XSS

---

## Architecture

```
┌─────────────────────────────────────────────┐
│            Streamlit Frontend                │
│  Welcome Screen → Trip Form → 12-Tab Dashboard│
│  SQLite (save/load trips) | PDF Export       │
└──────────────────────┬──────────────────────┘
                       │ POST /plan-trip
                       ▼
┌─────────────────────────────────────────────┐
│            FastAPI Backend                   │
│  URL validation | JSON parsing | Scoring     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│         CrewAI Orchestrator                  │
│                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │  Hotel   │ │Attraction│ │ Weather  │    │
│  │  Agent   │ │  Agent   │ │  Agent   │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│       │             │            │            │
│       ▼             ▼            ▼            │
│  SerpAPI Search  SerpAPI   OpenWeather API   │
│                   Search   + Forecast API     │
│                                              │
│  ┌──────────┐ ┌──────────────────────┐      │
│  │  Budget  │ │  Travel Planner      │      │
│  │  Agent   │ │  Agent (compiles)    │      │
│  └────┬─────┘ └──────────┬───────────┘      │
│       │                   │                   │
│       ▼                   ▼                   │
│  SerpAPI + Calc    Structured JSON Output     │
└─────────────────────────────────────────────┘
```

---

## Folder Structure

```
aitravelnew/
├── backend/
│   ├── agents.py          # 5 CrewAI agent definitions with LiteLLM monkeypatch
│   ├── tasks.py           # Task definitions with JSON-only output enforcement
│   ├── crew.py            # CrewAI crew orchestration, pre-fetches weather/hotels
│   ├── services.py        # WeatherService (current + forecast), SerpService
│   ├── tools.py           # 6 CrewAI tools (SerpSearch, Hotel, Attraction, Weather, TravelInfo, Restaurant)
│   ├── config.py          # Pydantic Settings (reads .env from project root)
│   ├── models.py          # Pydantic request/response models (TripRequest, ItineraryResponse, etc.)
│   ├── schemas.py         # Agent output JSON schemas
│   ├── utils.py           # HTML sanitization, URL validation, JSON extraction, logging
│   ├── main.py            # FastAPI app with /plan-trip, /health, trip scoring, URL rewriting
│   └── requirements.txt   # Backend dependencies
├── frontend/
│   ├── app.py             # Streamlit UI (~1900 lines): welcome screen, 12-tab dashboard, responsive CSS
│   ├── db.py              # SQLite module: init_db, save_trip, load_trips, load_trip_by_id, delete_trip
│   └── requirements.txt   # Frontend dependencies
├── travel_planner.db      # SQLite database (auto-created on first run)
├── .env                   # API keys (not committed)
├── .env.example           # Environment variable template
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12 |
| **Backend** | FastAPI, Pydantic v2, Pydantic Settings |
| **AI Orchestration** | CrewAI 0.193+ with LiteLLM |
| **LLM** | Google Gemini (`gemini-3.1-flash-lite` by default) |
| **Search** | SerpAPI (hotels, attractions, restaurants, travel info) |
| **Weather** | OpenWeatherMap API (current weather + 5-day forecast) |
| **Frontend** | Streamlit 1.29+ |
| **Database** | SQLite3 (built-in, no external server) |
| **Charts** | Plotly (budget pie chart) |
| **PDF** | ReportLab 4.0+ |
| **Styling** | Custom CSS with glassmorphism, animations, responsive grid |
| **Fonts** | DM Sans (body), Playfair Display (headings) via Google Fonts |

---

## Installation

### Prerequisites

- Python 3.12+
- API keys for Google Gemini, SerpAPI, and OpenWeatherMap

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-travel-planner.git
   cd ai-travel-planner
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS/Linux
   venv\Scripts\activate           # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and fill in your API keys.

---

## Environment Variables

| Variable | Description | Required | Default |
|---|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (auth key) | Yes | — |
| `GOOGLE_API_KEY` | Fallback Gemini API key | No | — |
| `SERP_API_KEY` | SerpAPI key for web search | Yes | — |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key | Yes | — |
| `GEMINI_MODEL` | Gemini model to use | No | `gemini-3.1-flash-lite` |
| `BACKEND_URL` | Frontend-to-backend URL | No | `http://localhost:8000` |
| `HOST` | Backend server host | No | `0.0.0.0` |
| `PORT` | Backend server port | No | `8000` |

---

## Running the Application

### Option 1 — Auto-start (recommended)

The Streamlit frontend automatically starts the backend if it's not running:

```bash
streamlit run frontend/app.py
```

- **Frontend:** http://localhost:8501
- **Backend:** http://localhost:8000 (auto-started)

### Option 2 — Manual (separate terminals)

**Terminal 1 — Backend:**
```bash
python backend/main.py
```

**Terminal 2 — Frontend:**
```bash
streamlit run frontend/app.py
```

---

## How It Works

### 1. Welcome Screen
User enters their name. A personalized welcome screen displays trending destinations, feature highlights, and testimonials.

### 2. Trip Form
User fills in:
- Source city and destination
- Number of days and travellers
- Budget (USD)
- Interests (food, history, adventure, nightlife, shopping, culture, nature, photography, etc.)
- Hotel preference (budget / standard / luxury)

### 3. AI Processing
The backend pre-fetches real weather data and hotel/attraction search results, then passes them to 5 CrewAI agents who collaborate to produce a complete itinerary as structured JSON.

### 4. Results Dashboard (12 Tabs)

| Tab | Content |
|---|---|
| **Overview** | Trip summary, destination overview, quick stats |
| **Hotels** | 3 hotel recommendations with ratings, prices, amenities, pros/cons, Maps/Book/Website links |
| **Attractions** | 7+ attractions with descriptions, categories, entry fees, hours, ratings |
| **Itinerary** | Day-by-day plans with morning/afternoon/evening/night activities, meals, estimated costs |
| **Weather** | Glassmorphism hero card, 5 detail cards (humidity, wind, rain, sunrise, sunset), 3 extra cards, dynamic tips |
| **Budget** | Pie chart, status card (within/over budget), category progress bars, savings suggestions |
| **Food** | Restaurant recommendations with cuisine, ratings, price range, Maps/Website links |
| **Transport** | Getting-around options with mode icons, estimated time/cost, tips |
| **Travel Tips** | Travel tips, things to carry, best times to visit |
| **Packing** | Grouped packing checklist (documents, electronics, medicines, clothes, essentials) |
| **AI Insights** | Hidden gems, tourist traps, must-try food, safety tips, money tips, scam alerts, photo spots, sunrise spots |
| **Export** | PDF download, save trip, plan another trip |

### 5. Trip Scoring
Every trip gets a score out of 100 based on:

| Category | Points | What It Measures |
|---|---|---|
| Hotel Quality | 20 | Number of hotels, average rating, tier match with budget |
| Attractions | 20 | Number of attractions, ratings, interest matching |
| Budget Fit | 20 | How well the total cost fits the user's budget |
| Weather | 15 | Temperature comfort, rain probability, wind, severe weather |
| Itinerary Quality | 15 | Day coverage, structure, highlight variety |
| Food & Transport | 10 | Restaurant variety, transport completeness |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check (returns version) |
| `POST` | `/plan-trip` | Plan a complete trip (main endpoint) |

### POST /plan-trip

**Request:**
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

**Response (simplified):**
```json
{
  "trip_id": "trip_a1b2c3d4",
  "trip_summary": "...",
  "destination_overview": "...",
  "weather_summary": { "temperature": 18, "condition": "Partly Cloudy", "rain_chance": 20, ... },
  "recommended_hotels": [ { "name": "...", "rating": 4.5, "price_per_night": 180, ... } ],
  "attractions": [ { "name": "...", "category": "museum", "rating": 4.7, ... } ],
  "daily_plans": [ { "day_number": 1, "title": "...", "morning": "...", ... } ],
  "budget": { "total": 2400, "hotel": 960, "food": 600, ... },
  "restaurants": [ { "name": "...", "cuisine": "French", "rating": 4.6, ... } ],
  "transport_options": [ { "mode": "metro", "description": "...", ... } ],
  "ai_insights": { "hidden_gems": [...], "safety_tips": [...], ... },
  "travel_tips": [...],
  "things_to_carry": [...],
  "packing_checklist": { "documents": [...], "clothes": [...] },
  "trip_score": 87,
  "score_reasons": [ { "text": "3 quality hotels found", "type": "good" }, ... ],
  "maps_urls": { ... }
}
```

---

## Database Schema

SQLite database at project root (`travel_planner.db`), auto-created on first run:

```sql
CREATE TABLE trips (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name       TEXT NOT NULL,
    source_city     TEXT,
    destination     TEXT,
    num_days        INTEGER,
    budget          REAL,
    travellers      INTEGER,
    hotel_preference TEXT,
    interests       TEXT,          -- JSON array
    trip_json       TEXT NOT NULL, -- Full request + itinerary JSON
    pdf_path        TEXT,
    created_at      TEXT NOT NULL  -- ISO timestamp
);
```

Trips are filtered by `user_name` — each user only sees their own saved trips.

---

## Key Implementation Details

### CrewAI LiteLLM Monkeypatch
CrewAI's built-in LLM configuration has issues with API key injection. The fix in `agents.py` monkeypatches `litellm.completion` to force-inject the correct model and API key on every call:

```python
_original_completion = litellm.completion
def _patched_completion(*args, **kwargs):
    kwargs["api_key"] = _api_key
    kwargs["model"] = _llm_model
    return _original_completion(*args, **kwargs)
litellm.completion = _patched_completion
```

### Weather Forecast Enrichment
The `WeatherService` first fetches current weather from OpenWeatherMap, then calls the 5-day forecast endpoint to extract:
- **Rain probability** (`pop` field from forecast)
- **Sunrise/sunset** times
- **Pressure, visibility, cloud cover**

### URL Validation
All Google Maps URLs generated by the AI are validated and rewritten to the correct format:
```
https://www.google.com/maps/search/?api=1&query={place}+{city}
```

### HTML Sanitization
All AI-generated text passes through:
- `strip_html()` — removes all HTML tags
- `sanitize_text()` — strips tags + normalizes whitespace
- `esc()` — HTML entity escaping for display

### Mobile Responsive Design
Three breakpoints with no desktop regression:
- **1024px** — Full-width container
- **768px** — Vertical hero stack, 2-column grids, floating hamburger menu, 44px touch targets
- **480px** — Single-column weather, full-width buttons, smaller score ring

---

## Future Improvements

- Interactive destination maps with Folium
- Currency conversion integration
- Multi-language support
- Real-time flight price comparison
- Multi-city itineraries
- Booking API integration (Booking.com, Airbnb)
- User authentication (currently name-based sessions only)

---

## License

MIT
