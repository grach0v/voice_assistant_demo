import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_gmail_service():
    """Get Gmail service object using credentials from token.json"""
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('gmail', 'v1', credentials=creds)


def create_message(to: str, subject: str, body_text: str) -> dict:
    """Create a message for sending via Gmail API"""
    message = MIMEText(body_text)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}


def send_message(service, user_id: str, message: dict) -> dict:
    """Send an email message using Gmail API"""
    sent = service.users().messages().send(userId=user_id, body=message).execute()
    print(f"Message sent! ID: {sent['id']}")
    return sent


def send_confirmation_email(tracking_id: str, customer_name: str, customer_email: str, transcript: str):
    """Send a confirmation email to the customer after call completion"""
    try:
        service = get_gmail_service()
        subject = f"Call Completed - Package {tracking_id}"
        body_text = (
            f"Hello {customer_name},\n\n"
            f"Your call regarding package {tracking_id} has been completed.\n\n"
            f"Call Summary:\n{transcript}\n\n"
            f"Thank you for using our service!"
        )
        message = create_message(customer_email, subject, body_text)
        send_message(service, "me", message)
    except Exception as e:
        print(f"Failed to send email: {e}")
        # Don't fail the entire request if email fails
