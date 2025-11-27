import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

SMTP_SERVER_HOST = "localhost"
SMTP_SERVER_PORT = 1025
SMTP_SENDER_ADDRESS = "parkspree@donotreply.in"
SENDER_PASSWORD = ""

def send_email(to_address, subject, message, content='html', attachment_file=None):
    msg = MIMEMultipart()
    msg['From'] = SMTP_SENDER_ADDRESS
    msg['To'] = to_address
    msg['Subject'] = subject

    # Attach the message once
    if content == 'html':
        msg.attach(MIMEText(message, 'html'))
    else:
        msg.attach(MIMEText(message, 'plain'))

    # Attach file if provided
    if attachment_file:
        with open(attachment_file, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={attachment_file}',
        )
        msg.attach(part)  # Don't forget to attach the part!

    # Send the email (moved outside the if block)
    s = smtplib.SMTP(SMTP_SERVER_HOST, SMTP_SERVER_PORT)
    s.login(SMTP_SENDER_ADDRESS, SENDER_PASSWORD)
    s.send_message(msg)
    s.quit()

    return True