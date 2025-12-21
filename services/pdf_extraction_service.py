"""Service for downloading and extracting text from arXiv PDFs."""

import httpx
import fitz
import logging

logger = logging.getLogger(__name__)


class PdfExtractionService:
    """Service for downloading PDFs from arXiv and extracting text."""

    BASE_URL = "https://export.arxiv.org/pdf"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        logger.info("PdfExtractionService initialized")

    async def close(self):
        await self.client.aclose()
        logger.info("PdfExtractionService closed")

    async def download_pdf(self, arxiv_id: str) -> bytes:
        """Download a PDF from arXiv."""
        url = f"{self.BASE_URL}/{arxiv_id}"
        logger.info(f"Downloading PDF: {arxiv_id}")

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            logger.info(f"Downloaded PDF: {len(response.content) / 1024:.1f} KB")
            return response.content

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading PDF: {e.response.status_code}")
            raise Exception(f"Failed to download PDF: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Network error downloading PDF: {e}")
            raise Exception(f"Network error downloading PDF: {e}")

    def extract_first_page_text(self, pdf_bytes: bytes) -> str:
        """Extract text from the first page of a PDF."""
        try:
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

            if len(pdf_document) == 0:
                logger.warning("PDF has no pages")
                return ""

            text = pdf_document[0].get_text()
            pdf_document.close()

            logger.info(f"Extracted {len(text)} characters from first page")
            return text

        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            raise Exception(f"Failed to extract text from PDF: {e}")
