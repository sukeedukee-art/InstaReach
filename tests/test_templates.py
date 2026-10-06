import pytest
from templates.template_engine import TemplateEngine

def test_template_variable_replacement():
    subject_tpl = "Urgent diagnostic SLA for {{company_name}}"
    body_tpl = "Dear {{first_name}},\nWe provide coverage for clinics in {{location}}.\nBest,\n{{sender_name}}"

    context = {
        "company_name": "Royal Infirmary",
        "first_name": "Arthur",
        "location": "Edinburgh",
        "sender_name": "Dr. Vance"
    }

    subj, body = TemplateEngine.render_email(subject_tpl, body_tpl, context)
    assert subj == "Urgent diagnostic SLA for Royal Infirmary"
    assert "Dear Arthur," in body
    assert "clinics in Edinburgh." in body
    assert "Best,\nDr. Vance" in body

def test_missing_variables_graceful_handling():
    subject_tpl = "Support for {{company_name}}"
    body_tpl = "Dear {{first_name}},\nReporting support in {{location}}."

    context = {} # completely empty

    subj, body = TemplateEngine.render_email(subject_tpl, body_tpl, context)
    assert subj == "Support for your organisation"
    assert "Dear Colleague," in body
    assert "Reporting support in the UK." in body
