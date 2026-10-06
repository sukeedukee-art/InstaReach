TELERADIOLOGY_SYSTEM_INSTRUCTION = """You are an assistant helping a UK healthcare/teleradiology company create professional B2B outreach emails.
Personalize the supplied approved email template using only the information provided by the application.
Never invent company facts, contracts, partnerships, statistics, certifications, awards, locations, technologies, staff numbers, services or previous communication.
Never claim that the recipient requested information.
Never claim to have contacted the recipient previously.
Never fabricate regulatory or medical claims.
If company-specific information is unavailable, use a professional generic sentence.
Keep the email concise and professional.
Use UK business English.
Do not use aggressive sales language.
Return valid JSON with:
{
  "subject": "...",
  "body": "..."
}
"""

def build_personalization_prompt(
    lead_data: dict,
    campaign_data: dict,
    base_subject_template: str,
    base_body_template: str
) -> str:
    """Builds the structured prompt containing lead facts and base template for Gemini."""
    return f"""Please personalize the following outreach email for this specific recipient.

=== SENDER & CAMPAIGN DETAILS ===
Sender Name: {campaign_data.get('sender_name', 'Dr. Alistair Vance')}
Sender Company: {campaign_data.get('sender_company', 'UK Teleradiology Partners')}
Sender Email: {campaign_data.get('sender_email', 'outreach@uk-teleradiology-partners.co.uk')}
Campaign Focus: {campaign_data.get('description', 'UK Diagnostic Imaging & Teleradiology Capacity')}

=== RECIPIENT INFORMATION (USE ONLY THESE VERIFIED FACTS) ===
Contact Name: {lead_data.get('contact_name', '')}
First Name: {lead_data.get('first_name', '')}
Last Name: {lead_data.get('last_name', '')}
Job Title: {lead_data.get('job_title', '')}
Company / Organisation: {lead_data.get('company_name', '')}
Website: {lead_data.get('website', '')}
Location: {lead_data.get('location', '')}
Organisation Description: {lead_data.get('company_description', '')}
Notes / Context: {lead_data.get('notes', '')}

=== APPROVED BASE TEMPLATES ===
Subject Template:
{base_subject_template}

Body Template:
{base_body_template}

=== INSTRUCTIONS ===
1. Replace variables and weave in natural, highly relevant personalization based ONLY on the recipient facts above.
2. If the recipient has a specific job title or organisation type (e.g. NHS Trust, private imaging clinic, orthopedic group), tailor the tone respectfully to their clinical/operational priorities.
3. Return ONLY a JSON object with keys "subject" and "body".
"""
