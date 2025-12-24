# arXiv Globe Visualization Backend

## Project Goal

Production-ready FastAPI backend that extracts institutional affiliations from arXiv papers and provides geocoded data for interactive globe visualization. Showcases the international nature of scientific collaboration by mapping where researchers are located globally.

**Current Status:** Deployed to production on GCP Cloud Run with API key authentication.

**Deployment:** Live at https://arxiv-globe-backend-331484945482.europe-west3.run.app

## Technology Stack

- **Language:** Python 3.13+
- **Framework:** FastAPI (REST API)
- **Build Tool:** uv (dependency management)
- **PDF Processing:** PyMuPDF (fitz)
- **LLM Integration:** OpenAI client (via LiteLLM proxy)
- **Geocoding:** geopy with Nominatim (OpenStreetMap)
- **Data Validation:** Pydantic models
- **Rate Limiting:** slowapi (per-IP request throttling)
- **Deployment Target:** GCP Cloud Run (serverless containers)

## Architecture

Clean, minimal service architecture with focused responsibilities:

### Services Layer

**ArxivService** - Query arXiv API for papers by category with pagination support

**PdfExtractionService** - Download PDFs and extract first page text using PyMuPDF

**AffiliationLlmService** - Parse affiliations from PDF text using LLM (gpt-4o-mini via LiteLLM)

**GeocodingService** - Convert addresses to coordinates using Nominatim (rate-limited to 1 req/sec)

### Models Layer

**models/arxiv.py** - arXiv paper metadata (ArxivPaper, ArxivAuthor, ArxivQueryResponse)

**models/affiliation.py** - Affiliation data with geocoding (Affiliation, GeocodedPaper, GeocodingMetadata, PaperAuthor)

### API Endpoints

**`GET /`** - Health check

**`GET /papers/by-category?category={cat}&index={n}`** - Main production endpoint
- Fetches single paper from arXiv by category and index
- Downloads PDF and extracts first page text
- Parses affiliations using LLM
- Geocodes all affiliations to coordinates
- Returns complete GeocodedPaper with visualization data
- Designed for stateless polling by frontend

## Key Design Decisions

### Affiliation Extraction Approach

**Why not use arXiv API metadata?**
- arXiv API supports `<arxiv:affiliation>` field but it's rarely populated
- Even recent papers (2025) don't include affiliation metadata
- Solution: Extract from PDF text using LLM

**Why extract affiliations without author linkage?**
- For globe visualization, we only need unique institutions per paper
- No need to track which author belongs to which institution
- Simplifies data model and LLM prompt
- Reduces token usage and improves extraction reliability

**Why use LLM for parsing?**
- Academic papers have inconsistent affiliation formats
- Multiple layouts, languages, and styles across disciplines
- LLM handles edge cases better than regex/rule-based parsing
- Can extract structured data (institution, address, country) in one pass

### Technology Choices

**PyMuPDF (fitz) for PDF extraction:**
- Fast and reliable
- Good text layout preservation
- Works in-memory (no file I/O needed)

**LiteLLM proxy with gpt-4o-mini:**
- Cost-effective model for structured extraction
- OpenAI client compatible
- Low temperature (0.1) for consistent parsing

**geopy with Nominatim:**
- Free, no API key required
- Good for academic/research projects
- Simple query building (address + country works best)
- Respects rate limits automatically

### API Architecture: Stateless Polling

**Why no database/queue?**
- MVP focuses on simplicity
- Single-user application
- Frontend controls pace via polling
- Natural rate limiting via geocoding (1 req/sec)
- Processing time (~3-4s/paper) matches animation timing

**How it works:**
1. Frontend requests paper by category and index
2. Backend processes paper (PDF → LLM → Geocoding)
3. Returns geocoded paper
4. Frontend animates, then requests next paper when ready
5. Repeat until no more papers

## Data Flow

```
Frontend Request
   ↓
1. Query arXiv API by category + index (ArxivService)
   ↓
2. Download PDF (PdfExtractionService)
   ↓
3. Extract first page text (PdfExtractionService)
   ↓
4. Parse affiliations with LLM (AffiliationLlmService)
   ↓
5. Geocode addresses to coordinates (GeocodingService)
   ↓
6. Return GeocodedPaper response
   ↓
Frontend renders on globe
```

## Security

Three-layer defense-in-depth security architecture:

### 1. Rate Limiting (Implemented)
- **Per-IP throttling:** 20 requests/minute using slowapi
- **Protection:** Prevents DDoS attacks and API abuse
- **Implementation:** In-memory rate limiting with get_remote_address key function
- **Response:** Returns HTTP 429 when limit exceeded
- **Testing:** test_rate_limit.py script for verification

### 2. API Key Authentication (Implemented)
- **Protection:** Prevents unauthorized access to backend
- **Implementation:** Custom `X-API-Key` header validation using FastAPI dependencies
- **Storage:** Environment variable `BACKEND_API_KEY` in both backend and frontend
- **Architecture:** Next.js BFF (Backend-for-Frontend) pattern - API key never exposed to browser
- **Status:** ✅ Deployed and operational

### 3. CORS Restriction (Planned)
- **Protection:** Browser-level security against cross-origin attacks
- **Implementation:** FastAPI CORS middleware restricted to Vercel domain
- **Current:** Wide open (allow_origins=["*"]) for development
- **Status:** Will restrict once Vercel domain is known
- **Note:** CORS doesn't affect curl/scripts, only browser requests

**Security Philosophy:**
- Defense in depth: Multiple security layers
- Fail secure: Each layer provides independent protection
- Development friendly: CORS restriction doesn't block local testing with curl
- Cost protection: Rate limiting prevents LLM credit drain

## Current Status

✅ **Deployed to Production:**
- Clean, minimal codebase (main.py: 219 lines, all services < 100 lines)
- Deployed to GCP Cloud Run (europe-west3 region)
- API key authentication implemented (X-API-Key header)
- Single production endpoint: `/papers/by-category` (requires API key)
- Health check endpoint: `/` (rate-limited, public)
- Complete pipeline: arXiv → PDF → LLM → Geocoding
- Structured Pydantic models with validation
- Rate-limited geocoding (1 req/sec via Nominatim)
- API rate limiting (20 req/minute per IP on protected endpoint, 60 req/minute on health check)
- CORS enabled for frontend integration
- Comprehensive error handling and logging
- Docker containerized with multi-stage builds

📊 **Code Metrics:**
- main.py: 219 lines (down from 602)
- arxiv_service.py: 94 lines (down from 169)
- pdf_extraction_service.py: 59 lines (down from 168)
- affiliation_llm_service.py: 108 lines (down from 194)
- geocoding_service.py: 96 lines (down from 175)

⏳ **Future Enhancements:**
- Restrict CORS to Vercel domain (once frontend deployed)
- Database caching for processed papers
- Alternative geocoding providers (Google Maps API for higher rate limits)
- Scheduled daily execution for batch processing
- Secret Manager integration for enhanced security

## Deployment

### Production Deployment on GCP Cloud Run

**Service URL:** https://arxiv-globe-backend-331484945482.europe-west3.run.app

**Deployment Date:** December 24, 2024

**Configuration:**
- **Project:** arxiv-globe-backend
- **Region:** europe-west3 (Frankfurt, Germany)
- **Memory:** 512 MiB
- **CPU:** 1 vCPU
- **Timeout:** 300 seconds (5 minutes)
- **Min Instances:** 0 (scales to zero)
- **Max Instances:** 10
- **Authentication:** Public (unauthenticated) with API key validation at application level

### Why Cloud Run?

**Benefits over other serverless options:**
- **Container-based:** Full control over Python environment and dependencies
- **Long timeouts:** 300s allows for PDF processing + LLM + geocoding
- **Scales to zero:** Cost-effective ($0-5/month expected)
- **Persistent containers:** Rate limiter state and connection pooling work correctly
- **Better for geocoding:** Handles 1 req/sec Nominatim rate limit gracefully
- **No code changes:** FastAPI works as-is in container

**Cold Start Behavior:**
- After ~15 minutes idle → scales to zero
- First request after idle: 5-9 seconds (includes container startup)
- Subsequent requests: 3-4 seconds (normal processing time)

### Deployment Process

#### Prerequisites

1. **Install gcloud CLI:**
   ```bash
   brew install google-cloud-sdk
   ```

2. **Authenticate and set up project:**
   ```bash
   gcloud init
   gcloud config set project arxiv-globe-backend
   gcloud config set run/region europe-west3
   ```

3. **Enable required APIs:**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

4. **Grant permissions to Cloud Build service account:**
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe arxiv-globe-backend --format='value(projectNumber)')

   gcloud projects add-iam-policy-binding arxiv-globe-backend \
     --member=serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
     --role=roles/storage.admin

   gcloud projects add-iam-policy-binding arxiv-globe-backend \
     --member=serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com \
     --role=roles/run.admin

   gcloud projects add-iam-policy-binding arxiv-globe-backend \
     --member=serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com \
     --role=roles/iam.serviceAccountUser
   ```

#### Deploy Command

```bash
# Generate production API key (do this once)
openssl rand -hex 16

# Deploy to Cloud Run
gcloud run deploy arxiv-globe-backend \
  --source . \
  --region europe-west3 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars BACKEND_API_KEY=YOUR_PROD_KEY,NETLIGHT_API_KEY=YOUR_LLM_KEY,NETLIGHT_API_URL=https://llm-proxy.edgez.live/
```

**What this does:**
1. Uploads source code to Cloud Build (respects `.gcloudignore`)
2. Builds Docker image using `Dockerfile`
3. Pushes image to Artifact Registry
4. Deploys to Cloud Run with specified configuration
5. Sets environment variables as secrets

**Build time:** 2-5 minutes

#### Testing the Deployment

**Health check (no auth required):**
```bash
curl https://arxiv-globe-backend-331484945482.europe-west3.run.app/
```

**Protected endpoint (requires API key):**
```bash
curl -H "X-API-Key: YOUR_PROD_KEY" \
  "https://arxiv-globe-backend-331484945482.europe-west3.run.app/papers/by-category?category=cs.AI&index=0"
```

### Docker Configuration

**Multi-stage Dockerfile:**
- **Stage 1 (builder):** Install dependencies with uv
- **Stage 2 (runtime):** Copy only what's needed, run as non-root user

**Key features:**
- Python 3.13-slim base image
- uv package manager for fast dependency installation
- Virtual environment copied from builder stage
- Non-root user (appuser) for security
- Health check endpoint configured
- Optimized for layer caching

**Files:**
- `Dockerfile` - Multi-stage build configuration
- `.dockerignore` - Excludes unnecessary files (saves upload time)
- `.gcloudignore` - Controls what gets uploaded to Cloud Build

### Cost Estimates

**Expected monthly cost:** $0-5

**Breakdown:**
- Cloud Run: Free tier covers 2M requests/month
- Artifact Registry: Free tier covers 0.5 GB storage
- Cloud Build: Free tier covers 120 build-minutes/day
- Networking: Minimal egress charges

**For portfolio/demo use:** Likely stays within free tier

### Monitoring

**View logs:**
```bash
gcloud run services logs read arxiv-globe-backend --region europe-west3
```

**View service details:**
```bash
gcloud run services describe arxiv-globe-backend --region europe-west3
```

**Cloud Console:**
https://console.cloud.google.com/run?project=arxiv-globe-backend

## Environment Setup

### Local Development

Required environment variables (`.env` file):
```bash
BACKEND_API_KEY=dev_key_12345  # API key for authentication
NETLIGHT_API_KEY=sk-xxx        # LLM API authentication
NETLIGHT_API_URL=https://...    # LiteLLM proxy endpoint
```

### Production (Cloud Run)

Set via `--set-env-vars` flag in deployment command:
- `BACKEND_API_KEY` - Production API key (generate with `openssl rand -hex 16`)
- `NETLIGHT_API_KEY` - LLM API authentication
- `NETLIGHT_API_URL` - LiteLLM proxy endpoint

**Alternative:** Use Google Secret Manager for enhanced security (see deployment section)

## Development Philosophy

**Production-First Approach:**
- Minimal, clean code over extensive documentation
- Single production endpoint over multiple debug routes
- Essential logging only (no verbose debug output)
- Clear separation of concerns across services
- Pydantic models for automatic validation

**Code Cleanup (December 2025):**
- Removed all debug/exploration endpoints
- Trimmed verbose docstrings and comments
- Removed unused convenience methods
- Simplified logging (kept essential INFO logs only)
- Result: 64% reduction in codebase size while maintaining full functionality

**Running the Backend:**
```bash
cd globe-backend
uv sync                    # Install dependencies
uv run python main.py      # Start server on port 8000
```

**Testing the Endpoint:**
```bash
# Health check (no API key required)
curl "http://localhost:8000/"

# Protected endpoint without API key (should fail with 401)
curl "http://localhost:8000/papers/by-category?category=cs.AI&index=0"

# Protected endpoint with API key (should succeed)
curl -H "X-API-Key: dev_key_12345" \
  "http://localhost:8000/papers/by-category?category=cond-mat.str-el&index=0"
```

**Testing Production Deployment:**
```bash
# Health check
curl https://arxiv-globe-backend-331484945482.europe-west3.run.app/

# Get paper with API key
curl -H "X-API-Key: YOUR_PROD_KEY" \
  "https://arxiv-globe-backend-331484945482.europe-west3.run.app/papers/by-category?category=cs.AI&index=0"
```

**Testing Rate Limiting:**
```bash
# Local testing
uv run python test_rate_limit.py

# Production testing
uv run python test_rate_limit.py https://arxiv-globe-backend-331484945482.europe-west3.run.app
```
