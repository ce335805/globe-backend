"""
Pydantic models for arXiv API responses.

These models are similar to Kotlin data classes or Java DTOs.
Pydantic provides:
- Automatic validation (like Bean Validation in Spring)
- Type safety
- Serialization/deserialization
- IDE autocomplete support
"""

from pydantic import BaseModel, Field
from typing import Optional


class ArxivAuthor(BaseModel):
    """
    Represents a single author from an arXiv paper.

    This is like a DTO in Spring Boot - it holds structured data
    and validates it automatically.

    Attributes:
        name: Author's full name (required)
        affiliation: Institution/university (optional, not always provided)
    """
    name: str = Field(..., description="Author's full name")
    affiliation: Optional[str] = Field(None, description="Author's institution")

    class Config:
        # This allows the model to be used with ORM objects later if needed
        # Similar to @Data annotation in Lombok
        from_attributes = True


class ArxivPaper(BaseModel):
    """
    Represents a single paper from arXiv.

    This model captures the key metadata we need for our analysis.
    We can always add more fields later as we explore the API.

    Attributes:
        arxiv_id: Unique identifier (e.g., "2301.12345")
        title: Paper title
        authors: List of authors with their affiliations
        abstract: Paper abstract/summary
        published: Publication date string
        categories: Subject categories (e.g., ["cs.AI", "stat.ML"])
    """
    arxiv_id: str = Field(..., description="Unique arXiv identifier")
    title: str = Field(..., description="Paper title")
    authors: list[ArxivAuthor] = Field(default_factory=list, description="List of authors")
    abstract: str = Field(..., description="Paper abstract")
    published: str = Field(..., description="Publication date")
    categories: list[str] = Field(default_factory=list, description="Subject categories")

    class Config:
        from_attributes = True


class ArxivQueryResponse(BaseModel):
    """
    Wrapper for the complete API response.

    This helps us track metadata about the query itself,
    not just the papers returned.

    Attributes:
        total_results: Total matching papers (may be more than returned)
        papers: List of paper objects
        query: The original query string (for logging/debugging)
    """
    total_results: int = Field(..., description="Total number of results available")
    papers: list[ArxivPaper] = Field(default_factory=list, description="Retrieved papers")
    query: str = Field(..., description="Original search query")

    class Config:
        from_attributes = True
