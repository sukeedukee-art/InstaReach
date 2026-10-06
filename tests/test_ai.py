import pytest
import json
from unittest.mock import MagicMock, patch
from ai.gemini_client import GeminiClient
from ai.prompts import build_personalization_prompt

def test_gemini_client_json_parsing():
    client = GeminiClient(api_key="mock_test_key")
    
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"subject": "Specialist Teleradiology for St. Jude", "body": "Dear Dr. Smith,\\n\\nWe can provide MSK coverage."}'
    mock_model.generate_content.return_value = mock_response

    with patch.object(client, "_client", mock_model):
        res, err = client.generate_email_content("test prompt")
        assert err is None
        assert res is not None
        assert res["subject"] == "Specialist Teleradiology for St. Jude"
        assert "MSK coverage" in res["body"]

def test_gemini_client_handles_malformed_json():
    client = GeminiClient(api_key="mock_test_key")
    
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = 'This is not valid JSON at all.'
    mock_model.generate_content.return_value = mock_response

    with patch.object(client, "_client", mock_model):
        res, err = client.generate_email_content("test prompt")
        assert res is None
        assert err is not None
        assert "Malformed JSON" in err or "JSONDecodeError" in err
