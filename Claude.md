# arXiv Affiliation Extraction Backend

## Project Goal

Build a system to extract institutional affiliations from arXiv papers for geographic visualization on a globe. The goal is to showcase the international nature of scientific collaboration by visualizing where researchers are located globally.

**End Goal:** Lambda function (GCP or similar) that retrieves arXiv papers daily, extracts affiliations, geocodes them, and provides data for a globe visualization.

## Technology Stack

- **Language:** Python 3.13+
- **Framework:** FastAPI (REST API)
- **Build Tool:** uv (dependency management)
- **PDF Processing:** PyMuPDF (fitz)
- **LLM Integration:** OpenAI client (via LiteLLM proxy)
- **Geocoding:** geopy with Nominatim (OpenStreetMap)
- **Data Validation:** Pydantic models

## Architecture

The system follows a layered service architecture (similar to Spring Boot):

### Services Layer

1. **ArxivService** (`services/arxiv_service.py`)
   - Queries arXiv API for paper metadata
   - Searches by category, query, or recent papers
   - Supports pagination via `start` parameter
   - Returns structured paper information (title, authors, abstract, arxiv_id)

2. **PdfExtractionService** (`services/pdf_extraction_service.py`)
   - Downloads PDFs from arXiv
   - Extracts text from first page (where affiliations are located)
   - Uses PyMuPDF for text extraction

3. **AffiliationLlmService** (`services/affiliation_llm_service.py`)
   - Sends extracted PDF text to LLM
   - Parses institutional affiliations using structured prompts
   - Returns list of unique affiliations (institution, address, country)

4. **GeocodingService** (`services/geocoding_service.py`)
   - Converts addresses to latitude/longitude coordinates
   - Uses Nominatim (OpenStreetMap) geocoder via geopy
   - Rate-limited to 1 request/second (Nominatim policy)
   - Graceful error handling for failed geocoding

### Models Layer

1. **ArxivModels** (`models/arxiv.py`)
   - `ArxivPaper` - Paper metadata
   - `ArxivAuthor` - Author information
   - `ArxivQueryResponse` - API response wrapper

2. **AffiliationModels** (`models/affiliation.py`)
   - `Affiliation` - Institution with location data (lat/lon, geocoded flag)
   - `PaperAffiliations` - List of unique affiliations per paper
   - `GeocodedPaper` - Complete paper response with geocoded affiliations
   - `GeocodingMetadata` - Processing metadata (success rate, pagination)
   - `PaperAuthor` - Simple author representation

### Controller Layer (API Endpoints)

**Production Endpoints:**
- `GET /` - Health check and API info
- `GET /papers/by-category` - **Main endpoint** - Get single geocoded paper by category and index

**Debug/Exploration Endpoints:**
- `GET /explore/recent` - Get recent papers by category (metadata only)
- `GET /explore/search` - Custom arXiv search queries
- `GET /debug/raw` - View raw arXiv XML response
- `GET /debug/extract-pdf` - Test PDF text extraction
- `GET /debug/parse-affiliations` - Test LLM affiliation parsing
- `GET /debug/geocode-affiliations` - Test full pipeline with geocoding

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

✅ **MVP Complete:**
- arXiv API integration with pagination
- PDF download and text extraction
- LLM-based affiliation parsing
- Geocoding service (geopy + Nominatim)
- Stateless polling API (`/papers/by-category`)
- Structured Pydantic models
- Debug endpoints for testing

🎯 **Ready for Frontend:**
- Backend is production-ready for MVP
- Single endpoint handles complete pipeline
- Natural rate limiting via geocoding
- Frontend can control pace via polling

⏳ **Future Enhancements:**
- Database caching for processed papers
- Alternative geocoding providers (Google Maps, OpenCage)
- Batch processing endpoint
- Deployment to GCP Cloud Run
- CORS configuration for production frontend

## Environment Setup

Required environment variables (see `.env` file):
- `NETLIGHT_API_KEY` - LLM API authentication
- `NETLIGHT_API_URL` - LiteLLM proxy endpoint

## Development Notes

**Incremental approach:**
- Build and test each service independently
- Use debug endpoints to validate each step
- Keep code clean with clear separation of concerns
- Follow Spring Boot patterns (services, models, controllers)
