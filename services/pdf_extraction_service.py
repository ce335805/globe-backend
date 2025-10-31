"""
Service for downloading and extracting text from arXiv PDFs.

This service follows the same pattern as ArxivService:
- Uses httpx for async HTTP requests
- Downloads PDFs from arXiv
- Extracts text using pymupdf (fitz)

Similar to a @Service in Spring Boot that handles external resource fetching.
"""

import httpx
import fitz  # PyMuPDF library (imported as fitz for historical reasons)
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PdfExtractionService:
    """
    Service for downloading PDFs from arXiv and extracting text.

    Architecture parallel to ArxivService:
    - Has a BASE_URL for PDF downloads
    - Uses httpx.AsyncClient for HTTP operations
    - Provides clean async API for downloading
    - Provides sync API for text extraction (pymupdf is not async)
    """

    # arXiv PDF base URL - just append arxiv_id to get PDF
    # Example: https://export.arxiv.org/pdf/2510.26584v1
    BASE_URL = "https://export.arxiv.org/pdf"

    def __init__(self):
        """
        Initialize the HTTP client for downloading PDFs.

        Similar to ArxivService, we create a reusable async client
        for efficient connection pooling.
        """
        self.client = httpx.AsyncClient(
            timeout=60.0,  # PDFs can be large, allow more time
            follow_redirects=True
        )
        logger.info("PdfExtractionService initialized")

    async def close(self):
        """
        Cleanup method to close the HTTP client.

        Call this on application shutdown to release resources.
        Like @PreDestroy in Spring Boot.
        """
        await self.client.aclose()
        logger.info("PdfExtractionService HTTP client closed")

    async def download_pdf(self, arxiv_id: str) -> bytes:
        """
        Download a PDF from arXiv.

        Args:
            arxiv_id: The arXiv identifier (e.g., "2510.26584v1" or "2510.26584")

        Returns:
            bytes: The raw PDF file content

        Raises:
            Exception: If download fails

        Example:
            pdf_bytes = await service.download_pdf("2510.26584")
        """
        # Build the PDF URL
        # arXiv accepts both with and without version number
        url = f"{self.BASE_URL}/{arxiv_id}"

        logger.info(f"Downloading PDF from {url}")

        try:
            # Download the PDF
            response = await self.client.get(url)
            response.raise_for_status()

            pdf_size_kb = len(response.content) / 1024
            logger.info(f"Successfully downloaded PDF: {pdf_size_kb:.1f} KB")

            return response.content

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading PDF {arxiv_id}: {e.response.status_code}")
            raise Exception(f"Failed to download PDF: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Network error downloading PDF {arxiv_id}: {e}")
            raise Exception(f"Network error downloading PDF: {e}")

    def extract_first_page_text(self, pdf_bytes: bytes) -> str:
        """
        Extract text from the first page of a PDF.

        This is where affiliations are typically located in academic papers.

        Args:
            pdf_bytes: Raw PDF file content

        Returns:
            str: Extracted text from the first page

        Note:
            This method is synchronous because pymupdf (fitz) is not async.
            That's fine - the expensive part is the download, which is async.

        How pymupdf works:
            1. Opens PDF from memory (no file I/O needed)
            2. Loads first page
            3. Extracts text with layout preservation
            4. Returns as string

        Example:
            text = service.extract_first_page_text(pdf_bytes)
        """
        try:
            # Open PDF from bytes (no file needed!)
            # fitz.open() can work directly with bytes in memory
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Check if PDF has pages
            if len(pdf_document) == 0:
                logger.warning("PDF has no pages")
                return ""

            # Get the first page (index 0)
            first_page = pdf_document[0]

            # Extract text from the page
            # get_text() returns plain text with basic layout preservation
            text = first_page.get_text()

            # Close the document to free memory
            pdf_document.close()

            logger.info(f"Extracted {len(text)} characters from first page")

            return text

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise Exception(f"Failed to extract text from PDF: {e}")

    async def download_and_extract_first_page(self, arxiv_id: str) -> str:
        """
        Convenience method: Download PDF and extract first page in one call.

        This combines the two operations for simpler usage.

        Args:
            arxiv_id: The arXiv identifier

        Returns:
            str: Extracted text from the first page

        Example:
            text = await service.download_and_extract_first_page("2510.26584")
        """
        pdf_bytes = await self.download_pdf(arxiv_id)
        text = self.extract_first_page_text(pdf_bytes)
        return text
