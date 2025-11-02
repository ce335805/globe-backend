"""
Main FastAPI application for arXiv data exploration.

This is the entry point - similar to a class with @SpringBootApplication
in Spring Boot.

FastAPI basics:
- @app.get() decorator defines GET endpoints (like @GetMapping)
- async def for async handlers (like suspend fun in Kotlin)
- FastAPI handles serialization automatically (like Jackson in Spring)
"""

import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from services.arxiv_service import ArxivService
from services.pdf_extraction_service import PdfExtractionService
from services.affiliation_llm_service import AffiliationLlmService
from services.geocoding_service import GeocodingService
from models.arxiv import ArxivQueryResponse
from models.affiliation import (
    PaperAffiliations,
    GeocodedPaper,
    GeocodingMetadata,
    PaperAuthor
)

# Load environment variables from .env file
load_dotenv()

# Configure logging to see output in console
# Set level to INFO to see our logger.info() statements
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Global service instances (will be initialized in lifespan)
arxiv_service: ArxivService = None
pdf_service: PdfExtractionService = None
llm_service: AffiliationLlmService = None
geocoding_service: GeocodingService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown logic.

    This is similar to @PostConstruct and @PreDestroy in Spring Boot.
    It runs code when the application starts and stops.

    - Startup: Initialize the ArxivService
    - Shutdown: Clean up resources (close HTTP client)
    """
    global arxiv_service, pdf_service, llm_service, geocoding_service

    # STARTUP
    logger.info("Starting up application...")

    # Initialize services
    arxiv_service = ArxivService()
    pdf_service = PdfExtractionService()

    # Initialize LLM service with credentials from .env
    api_key = os.getenv("NETLIGHT_API_KEY")
    api_url = os.getenv("NETLIGHT_API_URL")

    if not api_key or not api_url:
        logger.error("Missing NETLIGHT_API_KEY or NETLIGHT_API_URL in environment")
        raise ValueError("LLM credentials not configured - check .env file")

    llm_service = AffiliationLlmService(
        api_key=api_key,
        api_url=api_url,
        model="gpt-4o-mini"  # Cost-effective model for testing
    )

    # Initialize geocoding service (no API key needed for Nominatim)
    geocoding_service = GeocodingService(user_agent="arxiv-globe-backend")

    logger.info("Application startup complete")

    yield  # Application runs here

    # SHUTDOWN
    logger.info("Shutting down application...")
    await arxiv_service.close()
    await pdf_service.close()
    # LLM service doesn't need cleanup
    logger.info("Application shutdown complete")


# Create the FastAPI application
# This is like creating a Spring Boot application context
app = FastAPI(
    title="arXiv Globe Visualization API",
    description="API for extracting and geocoding arXiv paper affiliations for globe visualization",
    version="0.1.0",
    lifespan=lifespan  # Register startup/shutdown logic
)

# Configure CORS for frontend access
# In development, allow all origins. In production, restrict to specific domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PRODUCTION ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint - basic health check.

    Try this: http://localhost:8000/
    You'll see a simple JSON response.
    """
    return {
        "message": "arXiv Globe Visualization API",
        "version": "0.1.0",
        "docs": "Visit /docs for interactive API documentation",
        "main_endpoint": "/papers/by-category"
    }


@app.get("/explore/recent", response_model=ArxivQueryResponse)
async def explore_recent_papers(
    category: str = "cs.AI",
    max_results: int = 5
):
    """
    Explore recent papers from a specific category.

    This endpoint fetches papers and logs detailed information to the console
    so you can inspect what data is available, especially author affiliations.

    Args:
        category: arXiv category (e.g., "cs.AI", "physics.gen-ph", "math.CO")
        max_results: Number of papers to fetch (1-100)

    Returns:
        JSON response with papers and their metadata

    Try this:
        http://localhost:8000/explore/recent?category=cs.AI&max_results=5

    Common categories to explore:
        - cs.AI: Artificial Intelligence
        - cs.LG: Machine Learning
        - physics.data-an: Data Analysis
        - math.ST: Statistics Theory
        - q-bio.QM: Quantitative Methods
    """
    # Validate max_results
    if max_results < 1 or max_results > 100:
        raise HTTPException(
            status_code=400,
            detail="max_results must be between 1 and 100"
        )

    logger.info(f"Fetching {max_results} recent papers from category: {category}")

    try:
        # Call our service to get papers
        result = await arxiv_service.get_recent_papers(
            category=category,
            max_results=max_results
        )

        # Log summary statistics
        logger.info(f"Successfully retrieved {len(result.papers)} papers")

        # Count how many authors have affiliations
        total_authors = sum(len(paper.authors) for paper in result.papers)
        authors_with_affiliation = sum(
            1 for paper in result.papers
            for author in paper.authors
            if author.affiliation
        )

        logger.info(f"Total authors: {total_authors}")
        logger.info(f"Authors with affiliations: {authors_with_affiliation} ({authors_with_affiliation/total_authors*100:.1f}%)")

        return result

    except Exception as e:
        logger.error(f"Error fetching papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/papers/by-category", response_model=GeocodedPaper)
async def get_paper_by_category(
    category: str = "cs.AI",
    index: int = 0
):
    """
    Get a single geocoded paper from a category by index.

    This endpoint is designed for stateless polling from the frontend.
    The frontend requests papers one at a time as needed for visualization.

    Args:
        category: arXiv category (e.g., "cs.AI", "cond-mat", "hep-th")
        index: Zero-based index of paper to retrieve (0 = most recent)

    Returns:
        Single paper with geocoded affiliations

    Workflow:
        1. Frontend requests paper 0 → processes → animates
        2. When ready, requests paper 1 → processes → animates
        3. Continues until no more papers

    Example categories:
        - cs.AI: Artificial Intelligence
        - cs.LG: Machine Learning
        - cond-mat: Condensed Matter Physics
        - cond-mat.str-el: Strongly Correlated Electrons
        - hep-th: High Energy Physics - Theory
        - math.CO: Combinatorics
        - q-bio.NC: Neurons and Cognition

    Try it:
        http://localhost:8000/papers/by-category?category=cs.AI&index=0
        http://localhost:8000/papers/by-category?category=cond-mat&index=1
    """
    if index < 0:
        raise HTTPException(status_code=400, detail="index must be >= 0")

    try:
        logger.info(f"Fetching paper {index} from category {category}")

        # Fetch single paper using start parameter
        # arXiv's start parameter is 0-indexed, perfect for our use case
        result = await arxiv_service.search_papers(
            query=f"cat:{category}",
            start=index,
            max_results=1,
            sort_by="submittedDate",
            sort_order="descending"
        )

        if not result.papers:
            raise HTTPException(
                status_code=404,
                detail=f"No paper found at index {index} for category {category}"
            )

        paper = result.papers[0]
        logger.info(f"Processing paper: {paper.arxiv_id} - {paper.title}")

        # Step 1: Download PDF
        pdf_bytes = await pdf_service.download_pdf(paper.arxiv_id)

        # Step 2: Extract text from first page
        text = pdf_service.extract_first_page_text(pdf_bytes)

        # Step 3: Parse affiliations with LLM
        affiliations_result = llm_service.parse_affiliations(text)

        # Step 4: Geocode affiliations
        geocoded_affiliations = geocoding_service.geocode_affiliations(
            affiliations_result.affiliations
        )

        # Build response
        geocoded_count, total_count = geocoding_service.get_geocoded_count(
            geocoded_affiliations
        )

        logger.info(
            f"Paper processed: {geocoded_count}/{total_count} affiliations geocoded"
        )

        return GeocodedPaper(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            authors=[PaperAuthor(name=a.name) for a in paper.authors],
            abstract=paper.abstract,
            published=paper.published,
            categories=paper.categories,
            affiliations=geocoded_affiliations,
            metadata=GeocodingMetadata(
                index=index,
                category=category,
                total_affiliations=total_count,
                geocoded_affiliations=geocoded_count,
                has_more=index + 1 < result.total_results
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing paper: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DEBUG & EXPLORATION ENDPOINTS
# ============================================================================

@app.get("/debug/raw")
async def debug_raw_response(arxiv_id: str = "2301.00001"):
    """
    Debug endpoint to see the raw XML response from arXiv.

    This helps us understand what data is actually available in the API.

    Args:
        arxiv_id: A specific arXiv paper ID (e.g., "2301.00001")

    Returns:
        Raw XML text from arXiv API
    """
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://export.arxiv.org/api/query",
            params={"id_list": arxiv_id}
        )
        return {"raw_xml": response.text}


@app.get("/debug/extract-pdf")
async def debug_extract_pdf(arxiv_id: str = "2510.26584"):
    """
    Debug endpoint to download PDF and extract first page text.

    This endpoint:
    1. Downloads the PDF from arXiv
    2. Extracts text from the first page
    3. Prints full text to console (check your terminal!)
    4. Returns a summary to the browser

    Use this to verify PDF extraction is working before connecting to LLM.

    Args:
        arxiv_id: arXiv paper ID (e.g., "2510.26584" or "2510.26584v1")

    Returns:
        JSON with text length and preview

    Try it:
        http://localhost:8000/debug/extract-pdf?arxiv_id=2510.26584
    """
    try:
        logger.info(f"Debug: Extracting PDF for {arxiv_id}")

        # Download PDF
        pdf_bytes = await pdf_service.download_pdf(arxiv_id)

        # Extract text from first page
        text = pdf_service.extract_first_page_text(pdf_bytes)

        # Print to console for inspection
        print("\n" + "=" * 80)
        print(f"PDF TEXT EXTRACTION FOR: {arxiv_id}")
        print("=" * 80)
        print(text)
        print("=" * 80 + "\n")

        # Return summary to browser
        return {
            "arxiv_id": arxiv_id,
            "text_length": len(text),
            "preview": text[:500] + "..." if len(text) > 500 else text,
            "note": "Full text printed to console - check your terminal!"
        }

    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/parse-affiliations", response_model=PaperAffiliations)
async def debug_parse_affiliations(arxiv_id: str = "2510.26584"):
    """
    Debug endpoint to test the full pipeline: PDF extraction + LLM parsing.

    This endpoint:
    1. Downloads the PDF from arXiv
    2. Extracts text from first page
    3. Sends text to LLM for affiliation extraction
    4. Returns structured JSON with authors and affiliations
    5. Prints details to console

    Use this to verify the entire pipeline works before integrating
    into the main application flow.

    Args:
        arxiv_id: arXiv paper ID (e.g., "2510.26584")

    Returns:
        PaperAffiliations with structured author/affiliation data

    Try it:
        http://localhost:8000/debug/parse-affiliations?arxiv_id=2510.26584
    """
    try:
        logger.info(f"Debug: Full pipeline for {arxiv_id}")

        # Step 1: Download PDF
        logger.info("Step 1: Downloading PDF...")
        pdf_bytes = await pdf_service.download_pdf(arxiv_id)

        # Step 2: Extract text
        logger.info("Step 2: Extracting text from first page...")
        text = pdf_service.extract_first_page_text(pdf_bytes)

        # Step 3: Parse with LLM
        logger.info("Step 3: Parsing affiliations with LLM...")
        affiliations = llm_service.parse_affiliations(text)

        # Print results to console
        print("\n" + "=" * 80)
        print(f"AFFILIATION EXTRACTION RESULTS FOR: {arxiv_id}")
        print("=" * 80)
        print(f"Total unique affiliations: {len(affiliations.affiliations)}")
        print()

        for i, affiliation in enumerate(affiliations.affiliations, 1):
            print(f"{i}. {affiliation.institution}")
            print(f"   Address: {affiliation.address}")
            print(f"   Country: {affiliation.country}")
            print()

        if affiliations.notes:
            print(f"Notes: {affiliations.notes}")

        print("=" * 80 + "\n")

        logger.info("Pipeline completed successfully")
        return affiliations

    except Exception as e:
        logger.error(f"Error in full pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/geocode-affiliations", response_model=PaperAffiliations)
async def debug_geocode_affiliations(arxiv_id: str = "2510.26584"):
    """
    Debug endpoint to test the complete pipeline: PDF → LLM → Geocoding.

    This endpoint:
    1. Downloads the PDF from arXiv
    2. Extracts text from first page
    3. Sends text to LLM for affiliation extraction
    4. Geocodes all affiliations to coordinates
    5. Returns structured JSON with affiliations and coordinates
    6. Prints details to console

    Use this to verify the entire pipeline works including geocoding.

    Args:
        arxiv_id: arXiv paper ID (e.g., "2510.26584")

    Returns:
        PaperAffiliations with geocoded coordinates

    Try it:
        http://localhost:8000/debug/geocode-affiliations?arxiv_id=2510.26584
    """
    try:
        logger.info(f"Debug: Full pipeline with geocoding for {arxiv_id}")

        # Step 1: Download PDF
        logger.info("Step 1: Downloading PDF...")
        pdf_bytes = await pdf_service.download_pdf(arxiv_id)

        # Step 2: Extract text
        logger.info("Step 2: Extracting text from first page...")
        text = pdf_service.extract_first_page_text(pdf_bytes)

        # Step 3: Parse with LLM
        logger.info("Step 3: Parsing affiliations with LLM...")
        affiliations_result = llm_service.parse_affiliations(text)

        # Step 4: Geocode affiliations
        logger.info("Step 4: Geocoding affiliations...")
        geocoded_affiliations = geocoding_service.geocode_affiliations(
            affiliations_result.affiliations
        )

        # Update the result with geocoded data
        affiliations_result.affiliations = geocoded_affiliations

        # Print results to console
        print("\n" + "=" * 80)
        print(f"GEOCODED AFFILIATION RESULTS FOR: {arxiv_id}")
        print("=" * 80)

        geocoded_count, total_count = geocoding_service.get_geocoded_count(geocoded_affiliations)
        print(f"Total affiliations: {total_count}")
        print(f"Successfully geocoded: {geocoded_count} ({geocoded_count/total_count*100:.1f}%)")
        print()

        for i, affiliation in enumerate(geocoded_affiliations, 1):
            print(f"{i}. {affiliation.institution}")
            print(f"   Address: {affiliation.address}")
            print(f"   Country: {affiliation.country}")
            if affiliation.geocoded:
                print(f"   Coordinates: ({affiliation.latitude:.4f}, {affiliation.longitude:.4f}) ✓")
            else:
                print(f"   Coordinates: Not geocoded ✗")
            print()

        if affiliations_result.notes:
            print(f"Notes: {affiliations_result.notes}")

        print("=" * 80 + "\n")

        logger.info("Full pipeline with geocoding completed successfully")
        return affiliations_result

    except Exception as e:
        logger.error(f"Error in full pipeline with geocoding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/explore/search", response_model=ArxivQueryResponse)
async def explore_search(
    query: str,
    max_results: int = 5,
    sort_by: str = "submittedDate"
):
    """
    Search arXiv with a custom query.

    This gives you full control over the search query using arXiv syntax.

    Args:
        query: Search query using arXiv field prefixes
        max_results: Number of results (1-100)
        sort_by: Sort field - "relevance", "lastUpdatedDate", or "submittedDate"

    Returns:
        JSON response with matching papers

    Example queries:
        - "all:quantum computing" - search all fields
        - "ti:neural networks" - search titles only
        - "au:Hinton" - search by author
        - "cat:cs.AI AND ti:transformer" - category AND title search
        - "abs:climate AND cat:physics.ao-ph" - abstract search in specific category

    Try this:
        http://localhost:8000/explore/search?query=all:quantum%20computing&max_results=3
    """
    if max_results < 1 or max_results > 100:
        raise HTTPException(
            status_code=400,
            detail="max_results must be between 1 and 100"
        )

    logger.info(f"Searching arXiv with query: '{query}'")

    try:
        result = await arxiv_service.search_papers(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )

        logger.info(f"Search returned {len(result.papers)} papers (total available: {result.total_results})")

        return result

    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# This allows running the app directly with: python main.py
# Similar to if __name__ == "__main__" in standard Python scripts
if __name__ == "__main__":
    import uvicorn

    # uvicorn is the ASGI server (like Tomcat for Spring Boot)
    # It runs the FastAPI application
    uvicorn.run(
        "main:app",  # module:app_instance
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,  # Default port (like 8080 for Spring Boot)
        reload=True  # Auto-reload on code changes (like Spring DevTools)
    )
