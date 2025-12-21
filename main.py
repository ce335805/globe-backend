"""
Main FastAPI application for arXiv Globe Visualization.

Provides a single production endpoint for fetching geocoded arXiv papers
with institutional affiliations for globe visualization.
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
from models.affiliation import (
    GeocodedPaper,
    GeocodingMetadata,
    PaperAuthor
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Global service instances
arxiv_service: ArxivService = None
pdf_service: PdfExtractionService = None
llm_service: AffiliationLlmService = None
geocoding_service: GeocodingService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown logic."""
    global arxiv_service, pdf_service, llm_service, geocoding_service

    logger.info("Starting up application...")

    arxiv_service = ArxivService()
    pdf_service = PdfExtractionService()

    api_key = os.getenv("NETLIGHT_API_KEY")
    api_url = os.getenv("NETLIGHT_API_URL")
    if not api_key or not api_url:
        raise ValueError("Missing NETLIGHT_API_KEY or NETLIGHT_API_URL in .env")

    llm_service = AffiliationLlmService(
        api_key=api_key,
        api_url=api_url,
        model="gpt-4o-mini"
    )

    geocoding_service = GeocodingService(user_agent="arxiv-globe-backend")

    logger.info("Application startup complete")

    yield

    logger.info("Shutting down application...")
    await arxiv_service.close()
    await pdf_service.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="arXiv Globe Visualization API",
    description="API for extracting and geocoding arXiv paper affiliations",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "message": "arXiv Globe Visualization API",
        "version": "0.1.0",
        "endpoint": "/papers/by-category"
    }


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
    """
    if index < 0:
        raise HTTPException(status_code=400, detail="index must be >= 0")

    try:
        logger.info(f"Fetching paper {index} from category {category}")

        # Fetch single paper using start parameter
        # arXiv's start parameter is 0-indexed
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
