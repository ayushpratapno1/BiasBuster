<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Pandas-3.0-150458?style=for-the-badge&logo=pandas&logoColor=white" />
  <img src="https://img.shields.io/badge/Gemini_AI-2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" />
</p>

<h1 align="center">BiasBusters</h1>
<h3 align="center">Detect Bias. Build Fair AI.</h3>
<p align="center"><em>by Team Fairlytics</em></p>

---

## What is BiasBusters?

BiasBusters is an AI-powered web application that helps data scientists, researchers, and decision-makers **detect and understand hidden biases** in their datasets. Upload any CSV, pick a sensitive attribute (like gender, race, or age) and a target column, and get an instant fairness report complete with statistical analysis, interactive charts, and Gemini AI-generated explanations.

### Key Highlights

- **Zero storage** — fully stateless; no files, no sessions, no database writes
- **Production-safe** — runs on Render's free tier with no persistent storage required
- **AI-enhanced** — Google Gemini provides plain-language bias explanations on demand
- **Privacy-first** — the full dataset never leaves the browser-to-server POST; only summary statistics reach the AI

---

## Features

| Feature | Description |
|---|---|
| **CSV Upload** | Drag-and-drop or browse; validates format and enforces a 5 MB limit |
| **Auto-sampling** | Datasets over 5 000 rows are randomly sampled for fast analysis |
| **Smart Column Detection** | Automatically suggests sensitive columns (gender, race, age, etc.) |
| **Dataset Summary** | Row/column counts, data types, missing-value audit per column |
| **Bias Analysis** | Group-mean comparison across the sensitive attribute |
| **Fairness Score** | 0–100 % score based on min/max group outcome ratio |
| **Insight Generation** | Statistical insights with disparity calculations |
| **Bias Simulation** | One-click "what-if" removing the sensitive attribute |
| **AI Insights (Gemini)** | On-demand plain-language explanation of bias with mitigation steps |
| **Report Download** | Export a formatted `.txt` report of the full analysis |
| **Chart.js Visualisation** | Interactive bar chart of group outcome rates |

---

## Architecture

```
BiasBuster/
├── biasbusters/              # Django project package
│   ├── __init__.py
│   ├── settings.py           # Config — WhiteNoise, static files, upload limits
│   ├── urls.py               # Route table (5 endpoints)
│   ├── wsgi.py               # WSGI entry point (Gunicorn)
│   └── asgi.py               # ASGI entry point
├── detector/                 # Main application
│   ├── __init__.py
│   ├── apps.py               # App config
│   ├── models.py             # (empty — fully stateless)
│   ├── views.py              # All business logic (390 lines)
│   ├── admin.py
│   ├── tests.py
│   └── migrations/
├── templates/
│   ├── index.html            # Upload + column selection UI
│   └── result.html           # Results dashboard + charts + AI
├── static/                   # Static assets (served by WhiteNoise)
├── manage.py
├── requirements.txt
├── Procfile                  # Render / Heroku deploy config
└── README.md
```

---

## Application Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                           │
└──────────────┬──────────────────────────────────┬───────────────┘
               │                                  │
       ┌───────▼─────────┐                        │
       │  STEP 1: Upload │                        │
       │  CSV file (POST)│                        │
       └───────┬─────────┘                        │
               │                                  │
       ┌───────▼──────────────────────────────┐   │
       │         Django  ·  index view        │   │
       │                                      │   │
       │  1. Validate file (≤ 5 MB, CSV)      │   │
       │  2. pd.read_csv()                    │   │
       │  3. Sample to 5 000 rows if needed   │   │
       │  4. Build dataset summary            │   │
       │  5. Detect sensitive columns         │   │
       │  6. Compress: df → JSON → zlib → b64 │   │
       │  7. Render index.html (Step 2 UI)    │   │
       └───────┬──────────────────────────────┘   │
               │                                  │
               │  HTML with hidden <input>        │
               │  containing compressed dataset   │
               │                                  │
       ┌───────▼─────────┐                        │
       │  STEP 2: Select │                        │
       │  columns & POST │                        │
       └───────┬─────────┘                        │
               │                                  │
       ┌───────▼──────────────────────────────┐   │
       │         Django  ·  index view        │   │
       │                                      │   │
       │  1. Decompress: b64 → zlib → JSON    │   │
       │  2. pd.read_json() → DataFrame       │   │
       │  3. groupby(sensitive)[target].mean()│   │
       │  4. Compute fairness score           │   │
       │  5. Generate insights & suggestions  │   │
       │  6. Precompute simulation data       │   │
       │  7. Render result.html               │   │
       └───────┬──────────────────────────────┘   │
               │                                  │
               ▼                                  │
       ┌──────────────────┐                       │
       │   Results Page   │                       │
       │                  │    ┌───────────────┐  │
       │  • Fairness Score├───►  Chart.js bar  │  │
       │  • Bias alert    │    │  chart        │  │
       │  • Insights      │    └───────────────┘  │
       │  • Group rates   │                       │
       │                  │                       │
       │  ┌────────────┐  │    AJAX (lightweight) │
       │  │ Simulate   │──┼──► precomputed, no    │
       │  │ button     │  │    network call       │
       │  ├────────────┤  │                       │
       │  │ Download   │──┼──► POST /download-    │
       │  │ Report     │  │    report/            │
       │  ├────────────┤  │                       │
       │  │ AI Insights│──┼──► POST /ai-insights/ │
       │  │ (Gemini)   │  │    (summary only,     │
       │  └────────────┘  │     never full data)  │
       └──────────────────┘                       │
                                                  │
       ┌──────────────────────────────────────────▼──┐
       │          Google Gemini 2.5 Flash            │
       │                                             │
       │  Receives ONLY:                             │
       │  • sensitive column name                    │
       │  • target column name                       │
       │  • group outcome rates (dict)               │
       │  • fairness score                           │
       │  • bias detected flag                       │
       │                                             │
       │  Returns: structured markdown analysis      │
       └─────────────────────────────────────────────┘
```

---

## Stateless Data Transfer — How It Works

Traditional apps store uploaded data on disk or in sessions. BiasBusters does neither — it uses a **compressed hidden-field** approach:

```
Upload CSV
    │
    ▼
DataFrame ──► df.to_json() ──► zlib.compress() ──► base64.urlsafe_b64encode()
                                                          │
                                                          ▼
                                              <input type="hidden"
                                               name="dataset_json"
                                               value="eJy0lc9u2z...">
                                                          │
                                              User submits form (Step 2)
                                                          │
                                                          ▼
                                              base64.urlsafe_b64decode() ──► zlib.decompress()
                                                          │
                                                          ▼
                                                   pd.read_json()
                                                          │
                                                          ▼
                                                     DataFrame
```

**Why this works in production:**
- No session cookie size limits (cookie sessions cap at ~4 KB)
- No server-side file storage (Render's filesystem is ephemeral)
- Compression shrinks a typical 2 MB JSON payload to ~200–400 KB
- Base64 encoding is URL-safe for HTML form transport

---

## API Endpoints

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `GET`  | `/` | Landing page with upload form | — |
| `POST` | `/` | Step 1: upload CSV **or** Step 2: run analysis | CSRF |
| `POST` | `/simulate/` | Bias simulation (accepts compressed payload) | CSRF |
| `POST` | `/download-report/` | Generate and download `.txt` report | CSRF |
| `POST` | `/ai-insights/` | Gemini AI analysis (receives summary only) | CSRF |
| `GET`  | `/admin/` | Django admin panel | Staff |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 6.0, Python 3.12+ |
| **Data Processing** | Pandas 3.0 |
| **AI** | Google Gemini 2.5 Flash via `google-generativeai` |
| **Frontend** | Vanilla HTML/CSS/JS, Chart.js |
| **Static Files** | WhiteNoise (compressed, cache-friendly) |
| **WSGI Server** | Gunicorn |
| **Deployment** | Render (free tier compatible) |

---

## Getting Started

### Prerequisites

- Python 3.12 or higher
- A Google Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/your-username/BiasBuster.git
cd BiasBuster

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export GEMINI_API_KEY="your-google-api-key"        # Linux / macOS
set GEMINI_API_KEY=your-google-api-key             # Windows CMD
$env:GEMINI_API_KEY="your-google-api-key"          # Windows PowerShell

export ALLOWED_HOSTS="localhost 127.0.0.1"
set ALLOWED_HOSTS=localhost 127.0.0.1              # Windows CMD
$env:ALLOWED_HOSTS="localhost 127.0.0.1"           # Windows PowerShell

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Run the development server
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Deploy to Render

1. Push your code to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Connect your repository.
4. Set the build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
5. Set the start command: `gunicorn biasbusters.wsgi`
6. Add environment variables:

   | Key | Value |
   |-----|-------|
   | `GEMINI_API_KEY` | your Google API key |
   | `ALLOWED_HOSTS` | your-app.onrender.com |

7. Deploy.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes (for AI features) | Google Gemini API key. AI insights button gracefully degrades if missing. |
| `ALLOWED_HOSTS` | Yes | Space-separated list of allowed hostnames. |

---

## How to Use

1. **Upload** — Drag and drop a `.csv` file (up to 5 MB) or click to browse.
2. **Configure** — Pick the sensitive attribute (e.g. `gender`) and the target column (e.g. `hired`). The app auto-suggests sensitive columns.
3. **Analyze** — View your fairness score, bias alert, group outcome rates, and Chart.js visualisation.
4. **Simulate** — Click "Simulate Without Sensitive Attribute" to see what a perfectly fair dataset would look like.
5. **AI Insights** — Click "Generate AI Insights" for a Gemini-powered plain-language explanation with real-world impact analysis and mitigation steps.
6. **Download** — Export the full analysis as a formatted `.txt` report.

---

## Sample CSV Format

Any CSV with at least one categorical column and one numerical column works. Example:

```csv
name,gender,age,score,hired
Alice,Female,29,85,1
Bob,Male,34,78,1
Carol,Female,41,92,0
Dave,Male,25,65,1
Eve,Non-binary,38,88,0
```

- **Sensitive attribute:** `gender`
- **Target column:** `hired`

---

## Security Considerations

- **No data persistence** — uploaded datasets are never written to disk, database, or session storage.
- **API key isolation** — the Gemini key is read from an environment variable, never hardcoded.
- **Minimal AI exposure** — only aggregate statistics (column names, group means, fairness score) are sent to Gemini, never raw data.
- **CSRF protection** — all POST endpoints are protected by Django's CSRF middleware.
- **Upload limits** — file size is capped at 5 MB with both client-side and server-side validation.

---

## Bias Detection Methodology

1. **Group Mean Comparison** — compute the mean of the target column grouped by the sensitive attribute.
2. **Fairness Score** — `(min_group_mean / max_group_mean) * 100`. A score of 100 % means perfect parity.
3. **Bias Threshold** — if the absolute difference between the highest and lowest group means exceeds **0.1**, bias is flagged.
4. **Disparity Ratio** — the disadvantaged group's outcome as a percentage of the advantaged group's outcome.

---

## Project Constraints & Design Decisions

| Constraint | Solution |
|-----------|----------|
| Render's ephemeral filesystem | No file writes; compressed hidden-field data transfer |
| Session cookie ~4 KB limit | Eliminated session storage entirely |
| Gemini API cost/latency | Only summary stats sent; Gemini 2.5 Flash for speed |
| Large CSV uploads | 5 MB hard limit + auto-sampling to 5 000 rows |
| Client-side performance | Chart.js renders on the client; simulation is precomputed |

---

## Team

**Team Fairlytics**

Built with purpose to make AI fairer, one dataset at a time.

---

## License

This project is open-source and available under the [MIT License](LICENSE).
