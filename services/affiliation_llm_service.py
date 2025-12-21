"""Service for extracting author affiliations from PDF text using LLM."""

import json
import logging
from openai import OpenAI
from models.affiliation import PaperAffiliations, Affiliation

logger = logging.getLogger(__name__)


class AffiliationLlmService:
    """Service for parsing author affiliations using LLM."""

    def __init__(self, api_key: str, api_url: str, model: str = "gpt-4o-mini"):
        """Initialize the LLM client."""
        self.client = OpenAI(api_key=api_key, base_url=api_url)
        self.model = model
        logger.info(f"AffiliationLlmService initialized with model: {model}")

    def parse_affiliations(self, pdf_text: str, paper_title: str = "") -> PaperAffiliations:
        """Extract author affiliations from PDF text using LLM."""
        try:
            logger.info(f"Parsing affiliations ({len(pdf_text)} chars)")

            prompt = self._build_prompt(pdf_text, paper_title)

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
                temperature=0.1,
                max_tokens=2000
            )

            response_text = response.choices[0].message.content.strip()
            affiliations_data = self._parse_json_response(response_text)
            paper_affiliations = PaperAffiliations(**affiliations_data)

            logger.info(f"Extracted {len(paper_affiliations.affiliations)} affiliations")
            return paper_affiliations

        except Exception as e:
            logger.error(f"Error parsing affiliations: {e}")
            raise

    def _build_prompt(self, pdf_text: str, paper_title: str = "") -> str:
        """Build the prompt for the LLM."""
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
        """Parse and clean the LLM's JSON response."""
        text = response_text.strip()

        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {text[:200]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")
