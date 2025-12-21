"""Service for interacting with the arXiv API."""

import httpx
import feedparser
import logging
from models.arxiv import ArxivAuthor, ArxivPaper, ArxivQueryResponse

logger = logging.getLogger(__name__)


class ArxivService:
    """Service class for querying the arXiv API."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        logger.info("ArxivService initialized")

    async def close(self):
        await self.client.aclose()
        logger.info("ArxivService closed")

    async def search_papers(
        self,
        query: str,
        max_results: int = 10,
        start: int = 0,
        sort_by: str = "submittedDate",
        sort_order: str = "descending"
    ) -> ArxivQueryResponse:
        """
        Search for papers on arXiv.

        Args:
            query: Search query (e.g., "cat:cs.AI")
            max_results: Maximum number of papers to return
            start: Starting index for pagination (0-based)
            sort_by: Sort field - "relevance", "lastUpdatedDate", or "submittedDate"
            sort_order: "ascending" or "descending"

        Returns:
            ArxivQueryResponse containing papers and metadata
        """
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }

        logger.info(f"Querying arXiv: {query} (start={start}, max={max_results})")

        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        logger.info(f"Received {len(feed.entries)} papers")

        papers = [self._parse_entry(entry) for entry in feed.entries]
        total_results = int(feed.feed.get("opensearch_totalresults", 0))

        return ArxivQueryResponse(
            total_results=total_results,
            papers=papers,
            query=query
        )

    def _parse_entry(self, entry: dict) -> ArxivPaper:
        """Parse a single entry from the arXiv feed."""
        arxiv_id = entry.id.split("/abs/")[-1]
        title = entry.title.replace("\n", " ").strip()
        abstract = entry.summary.replace("\n", " ").strip()
        published = entry.published
        categories = [tag["term"] for tag in entry.tags]

        authors = [
            ArxivAuthor(
                name=author_dict.get("name", "Unknown"),
                affiliation=author_dict.get("arxiv_affiliation")
            )
            for author_dict in entry.authors
        ]

        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            published=published,
            categories=categories
        )
