import secrets
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def generate_verification_code():
    """Генерирует случайный 5-значный цифровой код подтверждения."""
    return str(secrets.randbelow(100000)).zfill(5)

def send_verification_email(email, code):
    """
    Отправляет код подтверждения на указанный email через SMTP сервер.
    
    Args:
        email (str): Email получателя
        code (str): Код подтверждения
        
    Returns:
        bool: True если отправка успешна, иначе False
    """
    # Если установлен режим разработки, не отправляем реальные письма
    if current_app.config.get('TESTING', False):
        print(f"💌 [DEV MODE] Код подтверждения для {email}: {code}")
        return True
        
    try:
        msg = MIMEMultipart()
        msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = email
        msg['Subject'] = 'Код подтверждения для портала МарГУ'

        html = f"""
        <html>
            <body>
                <h2>Код подтверждения</h2>
                <p>Ваш код для подтверждения регистрации: <b>{code}</b></p>
                <p>Код действителен в течение 10 минут.</p>
                <hr>
                <small>Это автоматическое сообщение, не отвечайте на него.</small>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
            if current_app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            server.send_message(msg)

        print(f"📧 Код {code} успешно отправлен на {email}")
        return True

    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")
        return False

def send_notification_email(recipient_email, subject, message_html, message_text=None):
    """
    Отправляет информационное письмо пользователю.
    
    Args:
        recipient_email (str): Email получателя
        subject (str): Тема письма
        message_html (str): HTML содержимое письма
        message_text (str, optional): Текстовая версия письма
        
    Returns:
        bool: True если отправка успешна, иначе False
    """
    # Если установлен режим разработки, не отправляем реальные письма
    if current_app.config.get('TESTING', False):
        print(f"💌 [DEV MODE] Уведомление для {recipient_email}: {subject}")
        return True
        
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Добавляем текстовую версию, если она предоставлена
        if message_text:
            msg.attach(MIMEText(message_text, 'plain'))
            
        # Добавляем HTML версию
        msg.attach(MIMEText(message_html, 'html'))

        with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
            if current_app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            server.send_message(msg)

        print(f"📧 Уведомление \"{subject}\" успешно отправлено на {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        return False 