import re
from typing import Dict, Any

class TemplateEngine:
    """
    Safely renders email templates using double-curly syntax {{variable}}.
    Handles missing variables gracefully without raising exceptions or showing raw ugly errors.
    """

    ALLOWED_VARIABLES = [
        "contact_name",
        "first_name",
        "last_name",
        "company_name",
        "job_title",
        "website",
        "location",
        "sender_name",
        "sender_company",
        "sender_email",
        "company_description",
        "notes"
    ]

    # Regex to match {{variable_name}} or {{ variable_name }}
    VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

    @classmethod
    def extract_variables(cls, text: str) -> list[str]:
        """Extract all unique variable names found in text."""
        if not text:
            return []
        return list(set(cls.VARIABLE_PATTERN.findall(text)))

    @classmethod
    def render(cls, template_str: str, context: Dict[str, Any]) -> str:
        """
        Renders template string with provided context.
        If a variable is missing or None, replaces it with a clean fallback.
        """
        if not template_str:
            return ""

        # Normalize context keys to lowercase
        norm_context = {str(k).lower(): (str(v).strip() if v is not None else "") for k, v in context.items()}

        def replace_match(match):
            var_name = match.group(1).lower()
            val = norm_context.get(var_name, "")
            
            # Intelligent fallbacks for common missing fields
            if not val:
                if var_name in ("first_name", "contact_name"):
                    val = "Colleague"
                elif var_name == "company_name":
                    val = "your organisation"
                elif var_name == "location":
                    val = "the UK"
                else:
                    val = ""
            return val

        rendered = cls.VARIABLE_PATTERN.sub(replace_match, template_str)
        # Clean up any awkward double spaces resulting from empty variables
        rendered = re.sub(r' +', ' ', rendered)
        return rendered

    @classmethod
    def render_email(cls, subject_template: str, body_template: str, context: Dict[str, Any]) -> tuple[str, str]:
        """Renders both subject and body template."""
        subject = cls.render(subject_template, context)
        body = cls.render(body_template, context)
        return subject, body
