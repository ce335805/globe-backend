"""
Pydantic models for affiliation data extracted from PDFs via LLM.

These models are designed for geographic visualization on a globe.
Keep fields simple and focused on what's needed for geocoding.

Simplified approach: Extract all unique affiliations from a paper,
without linking them to specific authors.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Affiliation(BaseModel):
    """
    Represents an institutional affiliation.

    Designed for geocoding and globe visualization.
    Address granularity (city vs full address) doesn't matter much
    when viewing on a global scale.

    Attributes:
        institution: Institution name (e.g., "MIT", "Max Planck Institute")
        address: Location info - can be just city or full address (e.g., "Cambridge, MA" or "Berlin, Germany")
        country: Country name (e.g., "USA", "Germany")
        latitude: Geocoded latitude coordinate (set by geocoding service)
        longitude: Geocoded longitude coordinate (set by geocoding service)
        geocoded: Whether this affiliation has been successfully geocoded
    """
    institution: str = Field(..., description="Institution or university name")
    address: Optional[str] = Field(None, description="City or full address")
    country: str = Field(..., description="Country name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate (-90 to 90)")
    longitude: Optional[float] = Field(None, description="Longitude coordinate (-180 to 180)")
    geocoded: bool = Field(False, description="Whether geocoding was successful")

    class Config:
        from_attributes = True


class PaperAffiliations(BaseModel):
    """
    Affiliation data extracted from a paper.

    This is what the LLM returns after parsing the first page of a PDF.
    Contains all unique affiliations mentioned in the paper, without
    linking them to specific authors.

    Attributes:
        affiliations: List of all unique affiliations found in the paper
        notes: Optional notes about extraction issues
    """
    affiliations: List[Affiliation] = Field(
        default_factory=list,
        description="List of all unique affiliations in the paper"
    )
    notes: Optional[str] = Field(
        None,
        description="Notes about extraction (e.g., 'Some affiliations unclear')"
    )

    class Config:
        from_attributes = True


class PaperAuthor(BaseModel):
    """
    Simple author representation for API responses.
    """
    name: str = Field(..., description="Author's name")

    class Config:
        from_attributes = True


class GeocodingMetadata(BaseModel):
    """
    Metadata about the geocoding process for a paper.
    """
    index: int = Field(..., description="Index of this paper in the category")
    category: str = Field(..., description="arXiv category")
    total_affiliations: int = Field(..., description="Total number of affiliations")
    geocoded_affiliations: int = Field(..., description="Number of successfully geocoded affiliations")
    has_more: bool = Field(..., description="Whether more papers are available")

    class Config:
        from_attributes = True


class GeocodedPaper(BaseModel):
    """
    Complete paper response with geocoded affiliations.

    This is the main response model for the /papers/by-category endpoint.
    Contains all information needed by the frontend for globe visualization.
    """
    arxiv_id: str = Field(..., description="arXiv paper ID")
    title: str = Field(..., description="Paper title")
    authors: List[PaperAuthor] = Field(..., description="List of authors")
    abstract: str = Field(..., description="Paper abstract")
    published: datetime = Field(..., description="Publication date")
    categories: List[str] = Field(..., description="arXiv categories")
    affiliations: List[Affiliation] = Field(..., description="Geocoded affiliations")
    metadata: GeocodingMetadata = Field(..., description="Processing metadata")

    class Config:
        from_attributes = True
