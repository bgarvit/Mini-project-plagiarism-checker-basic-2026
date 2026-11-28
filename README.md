# Plagify — AI Detection & Original-Document Plagiarism Checker

Complete full-stack app with:

1. **Check AI Detection** — paste text or upload TXT/PDF/DOCX; probabilistic AI-likelihood score  
2. **Check Plagiarism** — compare a temporary document **only** against your registered original reference (not the internet)

Python **FastAPI** backend · HTML/CSS/JS frontend · optional **Supabase** storage · light/dark theme · auth (email + Google-ready)

## Requirements

- Python 3.10+
- (Optional) Supabase project
- (Optional) GPTZero or Sapling API key for commercial AI detection
- (Recommended) `lmscan` for offline AI detection without an API key

## Quick start (Local Development)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run_server.py
```

Open http://127.0.0.1:8000

### First use

1. Open **Sign in** → create an account (or demo Google if no client ID).  
2. **AI Detection** works without login.  
3. **Plagiarism** requires login → upload an **original** document → upload a **second** document to compare.

## Garvit Deployment

### Prerequisites

1. **Supabase Project** - Required for persistent storage (SQLite doesn't work on Garvit's serverless platform)
2. **Google Cloud Console Project** - For Google OAuth (optional but recommended)
3. **Garvit Account** - [garvit.com](https://garvit.com)

### Deploy to Garvit

1. **Push to GitHub** (if not already):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/plagify.git
   git push -u origin main
   ```

2. **Import in Garvit Dashboard**:
   - Go to [garvit.com/new](https://garvit.com/new)
   - Import your GitHub repository
   - Garvit will auto-detect the Python/FastAPI project

3. **Configure Environment Variables** in Garvit Dashboard > Settings > Environment Variables:
   ```
   PLAGIFY_SECRET_KEY=your-generated-secret (run: openssl rand -hex 32)
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_BUCKET=original-documents
   AI_DETECTION_PROVIDER=auto
   CORS_ORIGINS=https://your-app.garvit.app
   ```
   - Add all variables for **Production**, **Preview**, and **Development** environments

4. **Configure Google OAuth** (if using Google Sign-In):
   - In Google Cloud Console > APIs & Services > Credentials
   - Add your Garvit deployment URL to **Authorized JavaScript origins**:
     - `https://your-app.garvit.app`
   - Add to **Authorized redirect URIs**:
     - `https://your-app.garvit.app` (for token client flow)

5. **Deploy**:
   - Click **Deploy** in Garvit
   - Wait for build to complete
   - Your app will be live at `https://your-app.garvit.app`

### Important Notes for Garvit

- **Database**: SQLite is ephemeral on Garvit. **Supabase is required** for user accounts and original document storage.
- **File Uploads**: Temporary files are stored in `/tmp` which is cleared between invocations.
- **Static Files**: Frontend is served from `frontend/` directory via Garvit's CDN.
- **API Routes**: All `/api/*` requests route to the FastAPI serverless function.
- **CORS**: Automatically configured for your Garvit domain via `GARVIT_URL` env var.

### Custom Domain

1. In Garvit Dashboard > Settings > Domains
2. Add your custom domain
3. Update `CORS_ORIGINS` and `PRODUCTION_DOMAIN` environment variables
4. Update Google OAuth authorized origins/redirects

## AI detection providers

Set `AI_DETECTION_PROVIDER` in `.env`:

| Value | Behavior |
|--------|----------|
| `auto` (default) | Try **lmscan** → GPTZero → Sapling → built-in heuristic |
| `lmscan` | Local offline detector (`pip install lmscan`) |
| `gptzero` | Requires `GPTZERO_API_KEY` |
| `sapling` | Requires `SAPLING_API_KEY` |
| `heuristic` | Statistical heuristic only (always available, clearly labeled) |

Detection **never invents a successful remote result**. If a configured remote provider fails, you get an explicit error (or auto falls back).

Limitations are always returned: scores are probabilistic, not proof.

## Supabase (original documents)

1. Create a Supabase project.  
2. Create a **private** Storage bucket named `original-documents` (or match `SUPABASE_BUCKET`).  
3. Run `supabase/schema.sql` in the SQL Editor.  
4. Set in `.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_BUCKET=original-documents
```

**Never put the service-role key in frontend code.**

If Supabase is not configured, originals are stored in local SQLite (`data/plagify.db`).  
The **second** (comparison) document is processed in memory only and is not saved.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/ai-detection/analyze` | Text form field and/or file |
| GET | `/api/plagiarism/status` | Supabase / local mode |
| GET | `/api/plagiarism/original` | Original metadata (auth) |
| POST | `/api/plagiarism/original` | Register original (auth) |
| DELETE | `/api/plagiarism/original` | Delete original (auth) |
| POST | `/api/plagiarism/compare` | Compare temp file vs original (auth) |
| POST | `/api/auth/login` | Email login |
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/google` | Google OAuth-ready exchange |
| GET | `/api/health` | Health + config flags |

## Tests

```bash
pip install pytest
pytest tests/ -q
```

## Project layout

```
app/                 FastAPI app
  routes/            auth, ai_detection, plagiarism
  services/          ai_detector, document_processor, plagiarism_engine
  database/          supabase_client, original_store, sqlite_users
frontend/            dashboard + feature pages
supabase/schema.sql  tables + RLS
tests/               unit tests
```

## Privacy

- Comparison uploads are temporary; not written to Supabase Storage or permanent tables.  
- Only the registered original is retained.  
- Do not log document contents or secrets.

## Troubleshooting

- **503 on AI detection**: install `lmscan` or set an API key; or set `AI_DETECTION_PROVIDER=heuristic`.  
- **No original registered**: sign in and upload under Plagiarism step 1.  
- **Supabase errors**: verify URL, service-role key, bucket name, and schema.sql applied.  
