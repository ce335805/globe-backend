"""Geocoding service for converting affiliations to geographic coordinates."""

from typing import List
import logging
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from models.affiliation import Affiliation

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for geocoding institutional affiliations."""

    def __init__(
        self,
        user_agent: str = "arxiv-globe-backend",
        min_delay_seconds: float = 1.0
    ):
        """Initialize geocoding service."""
        self.geolocator = Nominatim(user_agent=user_agent)
        self.geocode = RateLimiter(
            self.geolocator.geocode,
            min_delay_seconds=min_delay_seconds
        )
        logger.info(f"GeocodingService initialized")

    def _build_query(self, affiliation: Affiliation) -> str:
        """Build a geocoding query string from affiliation data."""
        parts = []

        if affiliation.address:
            parts.append(affiliation.address)
        else:
            parts.append(affiliation.institution)

        parts.append(affiliation.country)
        return ", ".join(parts)

    def geocode_affiliation(self, affiliation: Affiliation) -> Affiliation:
        """Geocode a single affiliation."""
        query = self._build_query(affiliation)

        try:
            logger.info(f"Geocoding: {query}")
            location = self.geocode(query)

            if location:
                affiliation.latitude = location.latitude
                affiliation.longitude = location.longitude
                affiliation.geocoded = True
                logger.info(f"Success: {affiliation.institution} -> ({location.latitude:.4f}, {location.longitude:.4f})")
            else:
                logger.warning(f"No results: {query}")
                affiliation.geocoded = False

        except GeocoderTimedOut:
            logger.error(f"Timeout: {query}")
            affiliation.geocoded = False

        except GeocoderServiceError as e:
            logger.error(f"Service error: {query} - {e}")
            affiliation.geocoded = False

        except Exception as e:
            logger.error(f"Unexpected error: {query} - {e}")
            affiliation.geocoded = False

        return affiliation

    def geocode_affiliations(
        self,
        affiliations: List[Affiliation]
    ) -> List[Affiliation]:
        """Geocode multiple affiliations."""
        logger.info(f"Batch geocoding {len(affiliations)} affiliations")

        geocoded_affiliations = []
        success_count = 0

        for affiliation in affiliations:
            geocoded = self.geocode_affiliation(affiliation)
            geocoded_affiliations.append(geocoded)
            if geocoded.geocoded:
                success_count += 1

        logger.info(f"Batch complete: {success_count}/{len(affiliations)} successful")
        return geocoded_affiliations

    def get_geocoded_count(self, affiliations: List[Affiliation]) -> tuple[int, int]:
        """Count how many affiliations have been geocoded."""
        geocoded_count = sum(1 for aff in affiliations if aff.geocoded)
        return geocoded_count, len(affiliations)
