import os
import smtplib
from email.message import EmailMessage

def send_email(to: str, subject: str, body: str) -> bool:
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    use_tls = os.getenv('SMTP_USE_TLS', '1') == '1'
    mail_from = os.getenv('MAIL_FROM', user or 'no-reply@example.com')

    if not host or not user or not password:
        print(f"[send_email Fallback] To:{to} Subject:{subject} Body:{body}")
        return True

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = mail_from
        msg['To'] = to
        msg.set_content(body)

        if use_tls:
            with smtplib.SMTP(host, port) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"[send_email ERROR] {e}")
        return False