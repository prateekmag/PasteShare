import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Dummy WhatsApp and SMS senders (replace with real API integration)
def send_whatsapp(phone, message):
    # Integrate with Twilio, Gupshup, or other WhatsApp API here
    print(f"WhatsApp to {phone}: {message}")
    return True

def send_sms(phone, message):
    # Integrate with Twilio, MSG91, or other SMS API here
    print(f"SMS to {phone}: {message}")
    return True

def send_email(recipient, subject, message):
    # Configure these for your SMTP server
    SMTP_SERVER = 'smtp.example.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'your_username'
    SMTP_PASSWORD = 'your_password'
    SMTP_SENDER = 'noreply@example.com'

    msg = MIMEMultipart()
    msg['From'] = SMTP_SENDER
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_SENDER, recipient, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise e

# FCM notification (Firebase Cloud Messaging)
def send_fcm(device_tokens, title, body, data=None, server_key=None):
    """
    device_tokens: list of FCM device tokens (strings)
    title: notification title
    body: notification body
    data: optional dict of extra data
    server_key: FCM server key (if None, read from env FCM_SERVER_KEY)
    """
    import os
    import requests
    if server_key is None:
        server_key = os.getenv('FCM_SERVER_KEY')
    if not server_key:
        raise Exception('FCM server key not set')
    url = 'https://fcm.googleapis.com/fcm/send'
    headers = {
        'Authorization': f'key={server_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'registration_ids': device_tokens,
        'notification': {
            'title': title,
            'body': body,
        },
        'data': data or {},
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f'FCM error: {response.status_code} {response.text}')
        raise Exception(f'FCM error: {response.status_code}')
    return response.json()
