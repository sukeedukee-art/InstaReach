import os
import sys
# Ensure project root is on sys.path for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
from config.settings import reload_settings
from email_engine.smtp_provider import SmtpEmailProvider

# Reload environment variables to ensure latest .env values
reload_settings()

provider = SmtpEmailProvider()
ok, err = provider.test_connection()
print('Connection test:', ok, err)

if ok:
    # Send a test email to the configured Gmail address
    success, send_err = provider.send_email(
        sender_name='InstaReach Test',
        sender_email='instarad18@gmail.com',
        recipient_email='instarad18@gmail.com',
        subject='[InstaReach] SMTP Test Email',
        body_text='This is a test email sent from the InstaReach system to verify SMTP functionality.',
        attachment_paths=None,
        body_html=None,
    )
    print('Send email result:', success, send_err)
else:
    print('Skipping email send due to connection failure')
