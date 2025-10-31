"""
Pydantic models for affiliation data extracted from PDFs via LLM.

These models are designed for geographic visualization on a globe.
Keep fields simple and focused on what's needed for geocoding.

Simplified approach: Extract all unique affiliations from a paper,
without linking them to specific authors.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


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
    """
    institution: str = Field(..., description="Institution or university name")
    address: Optional[str] = Field(None, description="City or full address")
    country: str = Field(..., description="Country name")

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
