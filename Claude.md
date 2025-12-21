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

## Current Status

✅ **Production-Ready Backend:**
- Clean, minimal codebase (main.py: 219 lines, all services < 100 lines)
- Single production endpoint: `/papers/by-category`
- Complete pipeline: arXiv → PDF → LLM → Geocoding
- Structured Pydantic models with validation
- Rate-limited geocoding (1 req/sec via Nominatim)
- CORS enabled for frontend integration
- Comprehensive error handling and logging

📊 **Code Metrics:**
- main.py: 219 lines (down from 602)
- arxiv_service.py: 94 lines (down from 169)
- pdf_extraction_service.py: 59 lines (down from 168)
- affiliation_llm_service.py: 108 lines (down from 194)
- geocoding_service.py: 96 lines (down from 175)

⏳ **Future Enhancements:**
- Database caching for processed papers
- Alternative geocoding providers (Google Maps API)
- Deployment to GCP Cloud Run
- Scheduled daily execution

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
