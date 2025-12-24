# arXiv Globe Visualization Backend

## Project Goal

Production-ready FastAPI backend that extracts institutional affiliations from arXiv papers and provides geocoded data for interactive globe visualization. Showcases the international nature of scientific collaboration by mapping where researchers are located globally.

**Current Status:** Clean, minimal production API with single endpoint for frontend integration.

**Future:** Deploy as serverless function (GCP Cloud Run) for daily arXiv data processing.

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

### 2. API Key Authentication (Planned)
- **Protection:** Prevents unauthorized access to backend
- **Implementation:** Custom header validation (e.g., X-API-Key)
- **Storage:** Environment variable for backend, Vercel environment for frontend
- **Status:** Deferred until frontend deployment to Vercel

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

✅ **Production-Ready Backend:**
- Clean, minimal codebase (main.py: 209 lines, all services < 100 lines)
- Single production endpoint: `/papers/by-category`
- Complete pipeline: arXiv → PDF → LLM → Geocoding
- Structured Pydantic models with validation
- Rate-limited geocoding (1 req/sec via Nominatim)
- API rate limiting (20 req/minute per IP)
- CORS enabled for frontend integration
- Comprehensive error handling and logging
- Test suite for rate limiting verification

📊 **Code Metrics:**
- main.py: 219 lines (down from 602)
- arxiv_service.py: 94 lines (down from 169)
- pdf_extraction_service.py: 59 lines (down from 168)
- affiliation_llm_service.py: 108 lines (down from 194)
- geocoding_service.py: 96 lines (down from 175)

⏳ **Next Steps:**
- Deploy to GCP Cloud Run
- Implement API key authentication
- Restrict CORS to Vercel domain
- Database caching for processed papers
- Alternative geocoding providers (Google Maps API)
- Scheduled daily execution

## Deployment

### GCP Cloud Run Architecture

**Why Cloud Run over pure serverless (Vercel Functions)?**
- Backend is functionally stateless but has infrastructure optimizations
- Rate limiter state and connection pooling benefit from persistent containers
- Cloud Run provides serverless benefits with container advantages
- Better suited for geocoding requirements (1 req/sec Nominatim limit)

**Advantages:**
- **No code changes:** Current architecture works as-is
- **Serverless benefits:** Scales to zero, pay-per-request pricing
- **Longer timeouts:** 60-minute request timeout (vs 10s on Vercel)
- **Cost-effective:** $0-1/month for low traffic
- **Container-based:** Full control over runtime environment

**Cold Start Trade-off:**
- After ~15 minutes of inactivity, container scales to zero
- Cold start adds ~2-5 seconds to first request (total 5-9s vs normal 3-4s)
- Acceptable for portfolio/demo use case
- Mitigation options: minimum instances ($10-15/month) or scheduled warming

**Frontend Architecture:**
- Frontend: Vercel (Next.js/React)
- Backend: GCP Cloud Run (FastAPI)
- Communication: CORS-restricted API calls with API key

**Deployment Status:** Not yet deployed (requires Dockerfile and gcloud configuration)

## Environment Setup

Required environment variables (see `.env` file):
- `NETLIGHT_API_KEY` - LLM API authentication
- `NETLIGHT_API_URL` - LiteLLM proxy endpoint

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
# Get first paper from condensed matter physics
curl "http://localhost:8000/papers/by-category?category=cond-mat.str-el&index=0"

# Get second paper from machine learning
curl "http://localhost:8000/papers/by-category?category=cs.LG&index=1"
```

**Testing Rate Limiting:**
```bash
# Run rate limit test (makes 25 requests, expects 20 to succeed)
uv run python test_rate_limit.py

# Test against deployed service
uv run python test_rate_limit.py https://your-cloud-run-url.run.app
```
