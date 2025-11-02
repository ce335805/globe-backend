"""
Geocoding service for converting institutional affiliations to geographic coordinates.

Uses geopy library with Nominatim (OpenStreetMap) as the default geocoder.
Implements rate limiting to respect API usage policies.

Architecture:
- Configurable geocoder backend (Nominatim default, easy to swap)
- Built-in rate limiting (1 request/second for Nominatim)
- Graceful error handling for failed geocoding attempts
- Returns updated Affiliation objects with lat/lon coordinates
"""

from typing import List, Optional
import logging
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from models.affiliation import Affiliation

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Service for geocoding institutional affiliations.

    Converts address information into latitude/longitude coordinates
    for globe visualization.

    Uses OpenStreetMap's Nominatim service by default (free, no API key).
    Rate limited to 1 request/second to respect usage policy.
    """

    def __init__(
        self,
        user_agent: str = "arxiv-globe-backend",
        min_delay_seconds: float = 1.0
    ):
        """
        Initialize geocoding service.

        Args:
            user_agent: Identifier for your application (required by Nominatim)
            min_delay_seconds: Minimum delay between requests (default 1.0 for Nominatim)
        """
        self.geolocator = Nominatim(user_agent=user_agent)
        self.geocode = RateLimiter(
            self.geolocator.geocode,
            min_delay_seconds=min_delay_seconds
        )
        logger.info(f"GeocodingService initialized with user_agent='{user_agent}'")

    def _build_query(self, affiliation: Affiliation) -> str:
        """
        Build a geocoding query string from affiliation data.

        Strategy:
        - Prefer address over institution (OpenStreetMap works better with addresses)
        - Always include country for disambiguation
        - Keep it simple - too much detail can confuse geocoders

        Args:
            affiliation: Affiliation object with institution/address/country

        Returns:
            Formatted query string for geocoder
        """
        parts = []

        # Prefer address if available (more specific for geocoding)
        if affiliation.address:
            parts.append(affiliation.address)
        else:
            # Fallback to institution name if no address
            parts.append(affiliation.institution)

        # Always add country for disambiguation
        parts.append(affiliation.country)

        query = ", ".join(parts)
        return query

    def geocode_affiliation(self, affiliation: Affiliation) -> Affiliation:
        """
        Geocode a single affiliation.

        Updates the affiliation object with latitude, longitude, and geocoded flag.

        Args:
            affiliation: Affiliation to geocode

        Returns:
            Updated affiliation with coordinates (if successful)
        """
        query = self._build_query(affiliation)

        try:
            logger.info(f"Geocoding: {query}")
            location = self.geocode(query)

            if location:
                affiliation.latitude = location.latitude
                affiliation.longitude = location.longitude
                affiliation.geocoded = True
                logger.info(
                    f"✓ Geocoded '{affiliation.institution}' to "
                    f"({location.latitude:.4f}, {location.longitude:.4f})"
                )
            else:
                logger.warning(f"✗ No results for: {query}")
                affiliation.geocoded = False

        except GeocoderTimedOut:
            logger.error(f"✗ Timeout geocoding: {query}")
            affiliation.geocoded = False

        except GeocoderServiceError as e:
            logger.error(f"✗ Service error geocoding '{query}': {e}")
            affiliation.geocoded = False

        except Exception as e:
            logger.error(f"✗ Unexpected error geocoding '{query}': {e}")
            affiliation.geocoded = False

        return affiliation

    def geocode_affiliations(
        self,
        affiliations: List[Affiliation]
    ) -> List[Affiliation]:
        """
        Geocode multiple affiliations.

        Processes each affiliation sequentially with rate limiting.
        Continues on errors (failed geocoding doesn't stop the batch).

        Args:
            affiliations: List of affiliations to geocode

        Returns:
            List of affiliations with coordinates where successful
        """
        logger.info(f"Starting batch geocoding of {len(affiliations)} affiliations")

        geocoded_affiliations = []
        success_count = 0

        for affiliation in affiliations:
            geocoded = self.geocode_affiliation(affiliation)
            geocoded_affiliations.append(geocoded)

            if geocoded.geocoded:
                success_count += 1

        logger.info(
            f"Batch geocoding complete: {success_count}/{len(affiliations)} successful"
        )

        return geocoded_affiliations

    def get_geocoded_count(self, affiliations: List[Affiliation]) -> tuple[int, int]:
        """
        Count how many affiliations have been geocoded.

        Args:
            affiliations: List of affiliations to check

        Returns:
            Tuple of (geocoded_count, total_count)
        """
        geocoded_count = sum(1 for aff in affiliations if aff.geocoded)
        return geocoded_count, len(affiliations)
