import json
import logging
import re
from typing import Optional, Tuple
from config.settings import GEMINI_API_KEY
from ai.prompts import TELERADIOLOGY_SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)

class GeminiClient:
    """Dedicated Gemini API client with graceful fallback and strict JSON parsing."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or GEMINI_API_KEY or "").strip()
        self._client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=TELERADIOLOGY_SYSTEM_INSTRUCTION,
                generation_config={"response_mime_type": "application/json"}
            )
            logger.info("Initialized Google Generative AI client.")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini Client: {e}")
            self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def generate_email_content(self, prompt: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Sends prompt to Gemini and parses the returned JSON.
        Returns (parsed_dict, error_message).
        parsed_dict should contain {"subject": "...", "body": "..."}
        """
        if not self.is_configured():
            return None, "Gemini API key is not configured. Please set GEMINI_API_KEY in .env or Settings."

        if not self._client:
            self._init_client()
            if not self._client:
                return None, "Failed to initialize Gemini GenerativeModel."

        try:
            response = self._client.generate_content(prompt)
            if not response or not response.text:
                return None, "Received empty response from Gemini AI."

            raw_text = response.text.strip()

            # Clean markdown codeblocks if present (e.g. ```json ... ```)
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if json_match:
                clean_json_str = json_match.group(0)
            else:
                clean_json_str = raw_text

            data = json.loads(clean_json_str)

            if not isinstance(data, dict):
                return None, "Gemini did not return a JSON object."

            if "subject" not in data or "body" not in data:
                return None, "Gemini JSON missing required 'subject' or 'body' keys."

            if not str(data["subject"]).strip() or not str(data["body"]).strip():
                return None, "Gemini generated an empty subject or body."

            return {
                "subject": str(data["subject"]).strip(),
                "body": str(data["body"]).strip()
            }, None

        except json.JSONDecodeError as jde:
            logger.error(f"Malformed JSON from Gemini: {jde}")
            return None, f"Malformed JSON from AI: {jde}"
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return None, f"Gemini API call failed: {str(e)}"
