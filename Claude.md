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
- **Data Validation:** Pydantic models

## Architecture

The system follows a layered service architecture (similar to Spring Boot):

### Services Layer

1. **ArxivService** (`services/arxiv_service.py`)
   - Queries arXiv API for paper metadata
   - Searches by category, query, or recent papers
   - Returns structured paper information (title, authors, abstract, arxiv_id)

2. **PdfExtractionService** (`services/pdf_extraction_service.py`)
   - Downloads PDFs from arXiv
   - Extracts text from first page (where affiliations are located)
   - Uses PyMuPDF for text extraction

3. **AffiliationLlmService** (`services/affiliation_llm_service.py`)
   - Sends extracted PDF text to LLM
   - Parses institutional affiliations using structured prompts
   - Returns list of unique affiliations (institution, address, country)

### Models Layer

1. **ArxivModels** (`models/arxiv.py`)
   - `ArxivPaper` - Paper metadata
   - `ArxivAuthor` - Author information
   - `ArxivQueryResponse` - API response wrapper

2. **AffiliationModels** (`models/affiliation.py`)
   - `Affiliation` - Institution with location data
   - `PaperAffiliations` - List of unique affiliations per paper

### Controller Layer

FastAPI endpoints in `main.py`:
- `/explore/recent` - Get recent papers by category
- `/explore/search` - Custom search queries
- `/debug/extract-pdf` - Test PDF text extraction
- `/debug/parse-affiliations` - Test full pipeline (PDF + LLM)

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

## Data Flow

```
1. User queries arXiv API
   ↓
2. Get paper metadata (ArxivService)
   ↓
3. Download PDF for each paper (PdfExtractionService)
   ↓
4. Extract first page text (PdfExtractionService)
   ↓
5. Send to LLM for affiliation parsing (AffiliationLlmService)
   ↓
6. Return structured affiliations (institution, address, country)
   ↓
7. [Future] Geocode affiliations to coordinates
   ↓
8. [Future] Visualize on globe
```

## Current Status

✅ **Completed:**
- arXiv API integration
- PDF download and text extraction
- LLM-based affiliation parsing
- Structured data models
- Debug endpoints for testing

🔄 **In Progress:**
- Testing and validation

⏳ **TODO:**
- Geocoding service (convert addresses to coordinates)
- Database storage for processed papers
- Orchestrator service to coordinate full pipeline
- Production endpoint for processing multiple papers
- Deployment to GCP as lambda function
- Scheduled daily execution

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
