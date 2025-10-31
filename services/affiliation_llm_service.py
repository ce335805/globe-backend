"""
Service for extracting author affiliations from PDF text using LLM.

This service uses OpenAI client (compatible with LiteLLM) to parse
affiliation information from the first page of academic papers.

Key design decisions:
- Extract all unique affiliations from paper (not linked to individual authors)
- City-level precision is sufficient for globe visualization
- Skip papers where extraction fails
"""

import json
import logging
from openai import OpenAI
from models.affiliation import PaperAffiliations, Affiliation

logger = logging.getLogger(__name__)


class AffiliationLlmService:
    """
    Service for parsing author affiliations using LLM.

    Uses OpenAI-compatible API (works with LiteLLM proxy) to extract
    structured affiliation data from PDF text.

    This service is different from ArxivService/PdfExtractionService:
    - No HTTP client needed (OpenAI SDK handles it)
    - Synchronous (most LLM calls are blocking)
    - Requires API credentials from environment
    """

    def __init__(self, api_key: str, api_url: str, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM client.

        Args:
            api_key: API key for authentication (from .env)
            api_url: Base URL for the LLM API (LiteLLM endpoint)
            model: Model to use (default: gpt-4o-mini for cost efficiency)

        Note: OpenAI client is configured to use custom base_url,
              so it works with LiteLLM proxy seamlessly.
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_url
        )
        self.model = model
        logger.info(f"AffiliationLlmService initialized with model: {model}")

    def parse_affiliations(self, pdf_text: str, paper_title: str = "") -> PaperAffiliations:
        """
        Extract author affiliations from PDF text using LLM.

        This is the main method that coordinates:
        1. Building the prompt
        2. Calling the LLM
        3. Parsing the JSON response
        4. Validating with Pydantic

        Args:
            pdf_text: Text extracted from first page of PDF
            paper_title: Optional paper title for context

        Returns:
            PaperAffiliations object with structured data

        Raises:
            Exception: If LLM call fails or response is invalid
        """
        try:
            logger.info(f"Parsing affiliations from text ({len(pdf_text)} chars)")

            # Build the prompt
            prompt = self._build_prompt(pdf_text, paper_title)

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured information from academic papers. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=2000   # Should be enough for most papers
            )

            # Extract response text
            response_text = response.choices[0].message.content.strip()

            logger.debug(f"LLM response: {response_text[:200]}...")

            # Parse JSON response
            affiliations_data = self._parse_json_response(response_text)

            # Validate with Pydantic
            paper_affiliations = PaperAffiliations(**affiliations_data)

            logger.info(f"Successfully extracted {len(paper_affiliations.affiliations)} affiliations")

            return paper_affiliations

        except Exception as e:
            logger.error(f"Error parsing affiliations: {e}")
            raise

    def _build_prompt(self, pdf_text: str, paper_title: str = "") -> str:
        """
        Build the prompt for the LLM.

        This is crucial! The prompt defines:
        - What to extract
        - Output format (JSON)
        - How to handle edge cases

        Args:
            pdf_text: Text from first page
            paper_title: Optional title for context

        Returns:
            Formatted prompt string
        """
        prompt = f"""Extract all unique institutional affiliations from this academic paper's first page.

{"Paper title: " + paper_title if paper_title else ""}

INSTRUCTIONS:
1. Find ALL unique affiliations mentioned in the paper (usually listed under author names)
2. Do NOT link affiliations to individual authors - just extract all unique institutions
3. For each affiliation, extract:
   - institution: The university/institute name (e.g., "MIT", "Max Planck Institute")
   - address: City or full address (e.g., "Cambridge, MA" or "Berlin, Germany")
   - country: Country name (e.g., "USA", "Germany", "UK")
4. Remove duplicate affiliations (same institution = one entry)
5. Return ONLY valid JSON, no other text

OUTPUT FORMAT:
{{
  "affiliations": [
    {{
      "institution": "Institution Name",
      "address": "City, State/Region",
      "country": "Country"
    }}
  ],
  "notes": "Optional notes about extraction quality"
}}

PDF TEXT:
{pdf_text[:3000]}

Return the JSON now:"""

        return prompt

    def _parse_json_response(self, response_text: str) -> dict:
        """
        Parse and clean the LLM's JSON response.

        LLMs sometimes return JSON wrapped in markdown code blocks.
        This method handles common formatting issues.

        Args:
            response_text: Raw text from LLM

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If JSON is invalid
        """
        # Remove markdown code blocks if present
        text = response_text.strip()

        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```

        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```

        text = text.strip()

        try:
            data = json.loads(text)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {text[:200]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")
