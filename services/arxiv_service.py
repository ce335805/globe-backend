"""
Service for interacting with the arXiv API.

This is similar to a @Service class in Spring Boot - it contains
the business logic for fetching and parsing arXiv data.

Key concepts:
- async/await: Non-blocking I/O (like Kotlin coroutines or Spring WebFlux)
- httpx: Modern HTTP client (like Spring's RestTemplate but async)
- feedparser: Parses Atom XML feeds into Python dicts
"""

import httpx
import feedparser
import logging
from typing import Optional
from models.arxiv import ArxivAuthor, ArxivPaper, ArxivQueryResponse

# Set up logging to see what's happening
# Similar to SLF4J/Logback in Spring Boot
logger = logging.getLogger(__name__)


class ArxivService:
    """
    Service class for querying the arXiv API.

    In Spring Boot terms, this would be annotated with @Service.
    It encapsulates all the logic for:
    - Making HTTP requests to arXiv
    - Parsing XML responses
    - Converting to our Pydantic models
    """

    # arXiv API base URL (similar to defining a @Value property in Spring)
    # Using HTTPS to avoid redirect issues
    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(self):
        """
        Constructor - initializes the HTTP client.

        We create an async HTTP client that will be reused for all requests.
        This is more efficient than creating a new client each time.
        """
        # httpx.AsyncClient is like RestTemplate but for async operations
        # follow_redirects=True ensures we handle HTTP -> HTTPS redirects
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        logger.info("ArxivService initialized")

    async def close(self):
        """
        Cleanup method to close the HTTP client.

        In Spring Boot, this would be a @PreDestroy method.
        Important for releasing resources properly.
        """
        await self.client.aclose()
        logger.info("ArxivService HTTP client closed")

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

        This is the main method you'll use to query the API.

        Args:
            query: Search query using arXiv syntax (e.g., "all:quantum" or "cat:cs.AI")
            max_results: Maximum number of papers to return (default 10, max 2000)
            start: Starting index for pagination (0-based)
            sort_by: Sort field - "relevance", "lastUpdatedDate", or "submittedDate"
            sort_order: "ascending" or "descending"

        Returns:
            ArxivQueryResponse containing the papers and metadata

        Example usage:
            service = ArxivService()
            results = await service.search_papers("cat:cs.AI", max_results=5)
            for paper in results.papers:
                print(f"{paper.title} by {[a.name for a in paper.authors]}")
        """
        # Build query parameters (similar to UriComponentsBuilder in Spring)
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }

        logger.info(f"Querying arXiv API with params: {params}")

        # Make the HTTP GET request
        # The 'await' keyword means "wait for this async operation to complete"
        # Similar to calling .block() on a Mono in Spring WebFlux
        response = await self.client.get(self.BASE_URL, params=params)

        # Raise an exception if the request failed (4xx or 5xx status)
        response.raise_for_status()

        # Parse the XML response
        # feedparser converts Atom XML into a Python dictionary
        feed = feedparser.parse(response.text)

        logger.info(f"Received {len(feed.entries)} papers from arXiv")

        # Convert the feed entries to our Pydantic models
        papers = []
        for entry in feed.entries:
            paper = self._parse_entry(entry)
            papers.append(paper)

            # Log each paper for exploration
            logger.info(f"Paper: {paper.title}")
            logger.info(f"  Authors: {len(paper.authors)}")
            for author in paper.authors:
                logger.info(f"    - {author.name} | Affiliation: {author.affiliation or 'NOT PROVIDED'}")

        # Get total results from the feed metadata
        # Note: This might not always be accurate for large result sets
        total_results = int(feed.feed.get("opensearch_totalresults", 0))

        return ArxivQueryResponse(
            total_results=total_results,
            papers=papers,
            query=query
        )

    def _parse_entry(self, entry: dict) -> ArxivPaper:
        """
        Parse a single entry from the arXiv feed into our ArxivPaper model.

        This is a private helper method (indicated by the _ prefix).
        It handles the messy work of extracting data from the XML structure.

        Args:
            entry: Dictionary representation of an Atom entry from feedparser

        Returns:
            ArxivPaper object with all the extracted data
        """
        # Extract the arXiv ID from the full URL
        # Example: "http://arxiv.org/abs/2301.12345v1" -> "2301.12345"
        arxiv_id = entry.id.split("/abs/")[-1]

        # Extract title and clean up whitespace
        title = entry.title.replace("\n", " ").strip()

        # Extract abstract and clean up whitespace
        abstract = entry.summary.replace("\n", " ").strip()

        # Extract publication date (ISO format string)
        published = entry.published

        # Extract categories (tags)
        # arXiv papers can have multiple subject categories
        categories = [tag["term"] for tag in entry.tags]

        # Parse authors with their affiliations
        authors = []
        for author_dict in entry.authors:
            name = author_dict.get("name", "Unknown")

            # Debug: Log the entire author dict to see what fields are available
            logger.debug(f"Author dict keys for {name}: {author_dict.keys()}")

            # Try different possible field names for affiliation
            # feedparser might use different naming conventions
            affiliation = (
                author_dict.get("arxiv_affiliation") or
                author_dict.get("affiliation") or
                author_dict.get("arxiv:affiliation") or
                None
            )

            authors.append(ArxivAuthor(name=name, affiliation=affiliation))

        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            published=published,
            categories=categories
        )

    async def get_recent_papers(self, category: str = "cs.AI", max_results: int = 10) -> ArxivQueryResponse:
        """
        Convenience method to get recent papers from a specific category.

        This is a common use case, so we provide a simpler interface.

        Args:
            category: arXiv category code (e.g., "cs.AI", "physics.gen-ph", "math.CO")
            max_results: Number of papers to retrieve

        Returns:
            ArxivQueryResponse with recent papers

        Common categories:
            - cs.AI: Artificial Intelligence
            - cs.LG: Machine Learning
            - physics.gen-ph: General Physics
            - math.CO: Combinatorics
            - q-bio.NC: Neurons and Cognition
        """
        query = f"cat:{category}"
        return await self.search_papers(
            query=query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending"
        )
