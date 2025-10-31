# arXiv Affiliation Extraction Backend

Backend service to extract institutional affiliations from arXiv papers for geographic visualization of scientific collaboration.

## Overview

This system retrieves papers from arXiv, downloads their PDFs, and uses LLM-based parsing to extract institutional affiliations. The extracted data will be used to visualize global scientific collaboration on an interactive globe.

## Project Structure

```
globe-backend/
├── main.py                           # FastAPI application entry point
├── models/
│   ├── arxiv.py                     # arXiv paper data models
│   └── affiliation.py               # Affiliation data models
├── services/
│   ├── arxiv_service.py             # arXiv API client
│   ├── pdf_extraction_service.py    # PDF download & text extraction
│   └── affiliation_llm_service.py   # LLM-based affiliation parsing
├── pyproject.toml                   # Dependencies
├── .env                             # Environment variables (not in git)
└── .example-env                     # Example environment config
```

## Prerequisites

- Python 3.13+
- uv (package manager)
- LLM API access (LiteLLM proxy)

## Setup & Installation

### 1. Install Dependencies

```bash
uv sync
```

This will install:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - Async HTTP client
- `feedparser` - XML/Atom feed parsing
- `pymupdf` - PDF text extraction
- `python-dotenv` - Environment variable loading
- `openai` - LLM API client (LiteLLM compatible)

### 2. Configure Environment Variables

Copy `.example-env` to `.env` and add your credentials:

```bash
cp .example-env .env
```

Edit `.env` with your actual values:
```
NETLIGHT_API_KEY=your-api-key-here
NETLIGHT_API_URL=https://your-llm-endpoint.com/
```

### 3. Run the Application

```bash
uv run python main.py
```

The server will start at `http://localhost:8000`

## Available Endpoints

### Exploration Endpoints

#### 1. Health Check
```
GET http://localhost:8000/
```
Basic health check endpoint.

#### 2. Explore Recent Papers
```
GET http://localhost:8000/explore/recent?category=cs.AI&max_results=5
```

Get recent papers from a specific arXiv category.

**Parameters:**
- `category` (optional): arXiv category code (default: "cs.AI")
- `max_results` (optional): Number of papers, 1-100 (default: 5)

**Common Categories:**
- `cs.AI` - Artificial Intelligence
- `cs.LG` - Machine Learning
- `cs.CL` - Computation and Language
- `physics.comp-ph` - Computational Physics
- `q-bio.QM` - Quantitative Methods

#### 3. Custom Search
```
GET http://localhost:8000/explore/search?query=all:quantum&max_results=3
```

Search arXiv with custom queries.

**Parameters:**
- `query` (required): Search query using arXiv syntax
- `max_results` (optional): Number of results, 1-100 (default: 5)
- `sort_by` (optional): "relevance", "lastUpdatedDate", "submittedDate"

**Query Examples:**
- `all:quantum computing` - Search all fields
- `ti:neural networks` - Search titles
- `au:Hinton` - Search by author
- `cat:cs.AI AND ti:transformer` - Boolean search

### Debug/Testing Endpoints

#### 4. Extract PDF Text
```
GET http://localhost:8000/debug/extract-pdf?arxiv_id=2510.26584
```

Downloads a PDF and extracts text from the first page. Useful for testing PDF extraction quality.

**Output:**
- JSON summary in browser
- Full extracted text in console/terminal

#### 5. Parse Affiliations (Full Pipeline)
```
GET http://localhost:8000/debug/parse-affiliations?arxiv_id=2510.26584
```

**This is the main endpoint for testing the complete pipeline:**
1. Downloads PDF from arXiv
2. Extracts first page text
3. Sends to LLM for affiliation parsing
4. Returns structured JSON

**Response Format:**
```json
{
  "affiliations": [
    {
      "institution": "MIT",
      "address": "Cambridge, MA",
      "country": "USA"
    },
    {
      "institution": "Stanford University",
      "address": "Stanford, CA",
      "country": "USA"
    }
  ],
  "notes": null
}
```

**Output:**
- Structured JSON in browser
- Formatted results in console

## Interactive API Documentation

FastAPI automatically generates interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test all endpoints directly from your browser using the "Try it out" feature!

## How It Works

### Pipeline Overview

```
1. Query arXiv API for papers (ArxivService)
   ↓
2. Download PDF for each paper (PdfExtractionService)
   ↓
3. Extract text from first page (PdfExtractionService)
   ↓
4. Send text to LLM for parsing (AffiliationLlmService)
   ↓
5. Return structured affiliations
   {institution, address, country}
```

### Why LLM-Based Extraction?

- arXiv API metadata rarely includes affiliation information
- Academic papers have inconsistent affiliation formats
- LLM can handle variations in layout, language, and style
- Extracts structured data in a single pass

### Data Model Design

**Affiliation:**
- `institution`: Institution name (e.g., "MIT")
- `address`: City or full address (e.g., "Cambridge, MA")
- `country`: Country name (e.g., "USA")

**Design Choice:** We extract unique affiliations per paper without linking them to individual authors. For globe visualization, we only need to know which institutions collaborated on a paper, not which specific author is at each institution.

## Example Usage

### Test a Single Paper

```bash
# Start the server
uv run python main.py

# In another terminal or browser:
curl "http://localhost:8000/debug/parse-affiliations?arxiv_id=2510.26584"
```

Check your terminal running the server for formatted output!

### Test Recent AI Papers

Visit http://localhost:8000/docs in your browser:
1. Find `/explore/recent`
2. Click "Try it out"
3. Set `category=cs.AI` and `max_results=10`
4. Click "Execute"

You'll get metadata for 10 recent AI papers. Pick an `arxiv_id` and test it with `/debug/parse-affiliations`.

## Development Notes

### Architecture Pattern

This project follows a layered architecture similar to Spring Boot:
- **Controllers:** FastAPI endpoints in `main.py`
- **Services:** Business logic (ArxivService, PdfExtractionService, etc.)
- **Models:** Pydantic data models for validation

### Service Lifecycle

Services are initialized at application startup and cleaned up at shutdown using FastAPI's lifespan context manager.

### Logging

All services log to console with INFO level. Check your terminal for:
- Service initialization
- HTTP requests (arXiv API, PDF downloads, LLM calls)
- Extraction results
- Error messages

## Troubleshooting

### "Missing NETLIGHT_API_KEY" Error
- Check that `.env` file exists
- Verify environment variables are set correctly
- Restart the server after editing `.env`

### PDF Download Fails
- Check arxiv_id format (e.g., "2510.26584" or "2510.26584v1")
- Verify arXiv is accessible from your network
- Check console logs for detailed error messages

### LLM Returns Invalid JSON
- Check your API credentials
- Verify LiteLLM endpoint is working
- Try with a different paper (some PDFs have unusual formatting)

## Next Steps

🔄 **Current:** Testing and validation of affiliation extraction

⏳ **TODO:**
- Geocoding service (convert addresses to coordinates)
- Database storage for processed papers
- Production endpoint for batch processing
- Orchestrator service for full pipeline
- Deployment to GCP as serverless function
- Scheduled daily execution

## Contributing

When continuing development:
1. Read `Claude.md` for detailed project context
2. Follow the incremental development approach
3. Test each component independently before integration
4. Update documentation as features are added

## License

See LICENSE file for details.
