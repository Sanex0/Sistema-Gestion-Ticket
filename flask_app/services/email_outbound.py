import smtplib
import logging
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_app.config.email_ingest import SMTP
from flask_app.config.conexion_login import execute_query


def _make_message_id(from_addr):
    domain = from_addr.split('@')[-1] if '@' in from_addr else 'localhost'
    return f"<{uuid.uuid4().hex}@{domain}>"


def send_email(to_email, subject, body, smtp_cfg=None, message_id=None, in_reply_to=None, id_msg=None, id_ticket=None, raw_headers=None):
    """
    Envía email y persiste Message-ID en `email_message_ids` si se proporciona `id_msg` o `id_ticket`.
    Retorna el Message-ID usado (string) o None en fallo.
    """
    cfg = smtp_cfg or SMTP
    host = cfg.get('HOST')
    port = cfg.get('PORT', 587)
    user = cfg.get('USER')
    password = cfg.get('PASSWORD')
    use_tls = cfg.get('USE_TLS', True)
    from_addr = cfg.get('FROM_ADDRESS') or user
    from_name = cfg.get('FROM_NAME', '')

    if not to_email:
        return None

    msg = MIMEMultipart()
    msg['From'] = f"{from_name} <{from_addr}>" if from_name else from_addr
    msg['To'] = to_email
    msg['Subject'] = subject

    # Message-ID
    if not message_id:
        message_id = _make_message_id(from_addr)
    msg['Message-ID'] = message_id

    # In-Reply-To / References
    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
        msg['References'] = in_reply_to

    msg.attach(MIMEText(body, 'plain'))

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(host, port, timeout=30)

        server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())
        server.quit()
        logging.info(f'Email enviado a {to_email} con asunto "{subject}" Message-ID={message_id}')

        # Persistir mapping Message-ID -> mensaje/ticket cuando corresponda
        if message_id and (id_msg or id_ticket):
            try:
                execute_query(
                    "INSERT INTO email_message_ids (message_id, id_msg, id_ticket, in_reply_to, raw_headers) VALUES (%s, %s, %s, %s, %s)",
                    (message_id.strip().lstrip('<').rstrip('>').lower(), id_msg, id_ticket, in_reply_to, raw_headers),
                    commit=True
                )
            except Exception:
                logging.exception('No se pudo insertar email_message_ids desde send_email')

        return message_id
    except Exception:
        logging.exception('Error enviando email')
        return None
