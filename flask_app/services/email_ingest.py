import imaplib
import email
import logging
import os
import traceback
import time
import argparse
import sys
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime, getaddresses
from flask_app.services.email_outbound import send_email

from flask_app.config.email_ingest import IMAP, ADDRESS_MAPPING, SMTP, SEND_AUTOREPLY
from flask_app.models.mensaje_model import MensajeModel
from flask_app.models.adjunto_model import AdjuntoModel
from flask_app.config.conexion_login import execute_query


def _decode_str(value):
    if not value:
        return ''
    if isinstance(value, str):
        return value
    try:
        parts = decode_header(value)
        decoded = ''
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded += part.decode(enc or 'utf-8', errors='ignore')
            else:
                decoded += part
        return decoded
    except Exception:
        return str(value)


def _get_body(msg):
    # Prefer text/plain
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get('Content-Disposition') or '')
            if ctype == 'text/plain' and 'attachment' not in disp:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except Exception:
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        # Fallback: first text/html without attachment
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get('Content-Disposition') or '')
            if ctype == 'text/html' and 'attachment' not in disp:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                except Exception:
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ''
    else:
        try:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        except Exception:
            return msg.get_payload()


def _strip_reply_text(body: str) -> str:
    if not body:
        return ''
    lines = body.splitlines()
    cleaned = []
    stop_markers = (
        '-----original message-----',
        '----original message----',
        'de:',
        'from:',
        'enviado:',
        'sent:',
        'para:',
        'to:',
        'asunto:',
        'subject:',
        'on ',
    )
    for line in lines:
        l = line.strip()
        if not l:
            cleaned.append(line)
            continue
        low = l.lower()
        if set(l) <= {'-', '_', '='}:
            # skip separator lines like "------"
            continue
        if low.startswith(stop_markers) and ('wrote' in low or low.startswith(('de:', 'from:', 'enviado:', 'sent:', 'para:', 'to:', 'asunto:', 'subject:'))):
            break
        if low.startswith('>'):
            break
        if low.startswith('-----original message-----'):
            break
        cleaned.append(line)
    return '\n'.join(cleaned).strip()


def _extract_message_id(value, pick='last'):
    if not value:
        return None
    try:
        text = str(value)
    except Exception:
        return None
    matches = re.findall(r'<([^>]+)>', text)
    if matches:
        selected = matches[-1] if pick == 'last' else matches[0]
        return selected.strip().lower()
    # Fallback: strip brackets and whitespace
    return text.strip().lstrip('<').rstrip('>').strip().lower()


def _save_attachments(msg, ticket_id, id_msg):
    saved = []
    for part in msg.walk():
        disp = str(part.get('Content-Disposition') or '')
        if part.get_content_maintype() == 'multipart':
            continue
        if 'attachment' in disp.lower() or part.get_filename():
            filename = part.get_filename()
            if filename:
                filename = _decode_str(filename)
            else:
                filename = 'adjunto'

            # Generar nombre único y guardar en carpeta del ticket
            ticket_dir = AdjuntoModel.obtener_ruta_por_ticket(ticket_id)
            unique_name = AdjuntoModel.generar_nombre_unico(filename)
            path = os.path.join(ticket_dir, unique_name)
            try:
                with open(path, 'wb') as f:
                    f.write(part.get_payload(decode=True) or b'')
                AdjuntoModel.crear_adjunto({'nom_adj': filename, 'ruta': path, 'id_msg': id_msg})
                saved.append(path)
            except Exception:
                logging.exception('Error guardando adjunto')
    return saved


def _map_recipient_to_depto(recipients):
    # recipients: list of emails
    for r in recipients:
        key = r.lower().strip()
        if key in ADDRESS_MAPPING:
            return ADDRESS_MAPPING[key]
    return None


def send_autoreply(to_email, ticket_id, original_subject, smtp_cfg=None):
    subject = f"Ticket #{ticket_id}: ({original_subject})"
    body = (
        f"Ticket #{ticket_id}: ({original_subject})\n\n"
        "Hola,\n\n"
        "Hemos recibido tu mensaje y hemos creado el ticket indicado arriba.\n"
        "Tu solicitud está en espera para ser tomada por el equipo de {depto}.\n\n"
        "Respuesta automática generada por el sistema.\n\n"
        "Gracias por contactarnos.\n\nAtentamente,\n{depto}"
    )
    depto = smtp_cfg.get('DEPTO_NOMBRE') if isinstance(smtp_cfg, dict) else None
    depto = depto or 'Soporte'
    body = body.format(depto=depto)
    # Persistiremos el Message-ID asociándolo al ticket para threading
    return send_email(to_email, subject, body, smtp_cfg=smtp_cfg, id_ticket=ticket_id, raw_headers=f"Auto-reply for ticket {ticket_id}")


def process_email_bytes(msg_bytes):
    try:
        msg = email.message_from_bytes(msg_bytes)
        # Extraer Message-ID / In-Reply-To para deduplicación y threading
        raw_message_id = msg.get('Message-ID')
        message_id = _extract_message_id(raw_message_id, pick='last')

        raw_in_reply = msg.get('In-Reply-To') or msg.get('References')
        in_reply_to = _extract_message_id(raw_in_reply, pick='last')

        # Si tenemos message-id, comprobar si ya fue procesado
        if message_id:
            try:
                existing = execute_query("SELECT message_id, id_msg, id_ticket FROM email_message_ids WHERE message_id = %s", (message_id,), fetch_one=True)
                if existing:
                    logging.info(f"Saltando mensaje duplicado Message-ID={message_id}")
                    return {'success': True, 'skipped': True, 'message_id': message_id, 'existing': existing}
            except Exception:
                logging.exception('Error consultando email_message_ids')
        subject = _decode_str(msg.get('Subject'))
        from_hdr = msg.get('From') or ''
        from_name, from_email = email.utils.parseaddr(from_hdr)
        from_name = _decode_str(from_name) or from_email.split('@')[0]

        logging.info('Procesando email: From=%s Subject=%s Message-ID=%s', from_email, subject, message_id)

        # Obtener destinatarios To + Cc
        tos = msg.get_all('To', []) or []
        ccs = msg.get_all('Cc', []) or []
        addrs = getaddresses(tos + ccs)
        recipient_emails = [a[1] for a in addrs if a and a[1]]

        body = _strip_reply_text(_get_body(msg))

        id_depto = _map_recipient_to_depto(recipient_emails)

        email_data = {
            'from_email': from_email,
            'from_name': from_name,
            'subject': subject or '(sin asunto)',
            'body': body,
            'id_depto': id_depto,
            'id_canal': 1,
            'message_id': message_id,
            'in_reply_to': in_reply_to,
            'raw_headers': '\n'.join([f"{k}: {v}" for k, v in msg.items()])
        }

        # Crear ticket + mensaje
        res = MensajeModel.crear_desde_email(email_data)
        id_msg = res.get('id_msg')
        ticket_id = res.get('id_ticket')

        # La deduplicación e inserción de message-id ya se realiza en MensajeModel.crear_desde_email

        # Guardar adjuntos si los hay
        if ticket_id and id_msg:
            _save_attachments(msg, ticket_id, id_msg)

        # Enviar respuesta automática si está habilitado
        try:
            if SEND_AUTOREPLY and ticket_id and res.get('created_ticket'):
                to_email = from_email
                original_subject = subject or '(sin asunto)'
                try:
                    depto_name = None
                    if email_data.get('id_depto'):
                        try:
                            depto_row = execute_query("SELECT descripcion FROM departamento WHERE id_depto = %s", (email_data.get('id_depto'),), fetch_one=True)
                            depto_name = (depto_row or {}).get('descripcion') if isinstance(depto_row, dict) else None
                        except Exception:
                            pass
                    smtp_cfg = dict(SMTP)
                    if depto_name:
                        smtp_cfg['DEPTO_NOMBRE'] = depto_name
                    send_autoreply(to_email, ticket_id, original_subject, smtp_cfg=smtp_cfg)
                except Exception:
                    logging.exception('No se pudo enviar respuesta automática')
        except Exception:
            logging.exception('Error al evaluar envío de respuesta automática')

        return res
    except Exception as e:
        logging.exception('Error procesando email')
        return {'success': False, 'error': str(e)}


def poll_once(imap_cfg=None):
    cfg = imap_cfg or IMAP
    host = cfg.get('HOST')
    port = cfg.get('PORT', 993)
    user = cfg.get('USER')
    password = cfg.get('PASSWORD')
    folder = cfg.get('FOLDER', 'INBOX')
    use_ssl = cfg.get('USE_SSL', True)
    search_criteria = os.getenv('IMAP_SEARCH') or cfg.get('SEARCH', 'UNSEEN')

    conn = None
    try:
        if use_ssl:
            conn = imaplib.IMAP4_SSL(host, port)
        else:
            conn = imaplib.IMAP4(host, port)

        conn.login(user, password)
        conn.select(folder)

        # Buscar emails según criterio configurado (por defecto: UNSEEN)
        if isinstance(search_criteria, (list, tuple)):
            search_args = list(search_criteria)
        else:
            search_args = str(search_criteria).split()

        typ, data = conn.search(None, *search_args)
        if typ != 'OK':
            return {'success': False, 'error': 'No se pudo buscar mensajes'}
        ids = data[0].split() if data and data[0] else []
        logging.info('poll_once: encontrados %s mensajes UNSEEN', len(ids))
        results = []
        for _id in ids:
            try:
                typ, msg_data = conn.fetch(_id, '(RFC822)')
                if typ != 'OK':
                    continue
                raw = msg_data[0][1]
                r = process_email_bytes(raw)
                results.append(r)
                # Marcar como SEEN
                conn.store(_id, '+FLAGS', '\\Seen')
            except Exception:
                logging.exception('Falla procesando mensaje IMAP')

        conn.logout()
        return {'success': True, 'processed': len(results), 'results': results}

    except Exception:
        logging.exception('Error conectando IMAP')
        return {'success': False, 'error': traceback.format_exc()}


def connect_and_idle_loop(imap_cfg=None, keepalive=300, min_backoff=5, max_backoff=600):
    cfg = imap_cfg or IMAP
    host = cfg.get('HOST')
    port = cfg.get('PORT', 993)
    user = cfg.get('USER')
    password = cfg.get('PASSWORD')
    folder = cfg.get('FOLDER', 'INBOX')
    use_ssl = cfg.get('USE_SSL', True)
    search_criteria = os.getenv('IMAP_SEARCH') or cfg.get('SEARCH', 'UNSEEN')

    if isinstance(search_criteria, (list, tuple)):
        search_args = list(search_criteria)
    else:
        search_args = str(search_criteria).split()

    backoff = min_backoff
    while True:
        conn = None
        try:
            logging.info('Conectando IMAP %s', host)
            conn = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
            conn.login(user, password)
            conn.select(folder)

            logging.info('Usando polling imaplib (keepalive=%ss, search=%s)', keepalive, ' '.join(search_args))
            while True:
                try:
                    typ, data = conn.search(None, *search_args)
                    if typ == 'OK':
                        ids = data[0].split() if data and data[0] else []
                        for _id in ids:
                            try:
                                typf, msg_data = conn.fetch(_id, '(RFC822)')
                                if typf != 'OK':
                                    continue
                                raw = msg_data[0][1]
                                process_email_bytes(raw)
                                conn.store(_id, '+FLAGS', '\\Seen')
                            except Exception:
                                logging.exception('Falla procesando mensaje IMAP en polling')
                    time.sleep(keepalive)
                    try:
                        conn.noop()
                    except Exception:
                        raise
                except Exception:
                    logging.exception('Error en bucle de polling — se reconectará')
                    break

        except Exception:
            logging.exception('Error en conexión IMAP')
            # Reconexión con backoff exponencial
            logging.info('Reconectando en %s segundos...', backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
        finally:
            try:
                if conn:
                    try:
                        conn.logout()
                    except Exception:
                        conn.shutdown = True
            except Exception:
                pass


if __name__ == '__main__':
    # Ejecutable: modo one-shot o modo persistente (--idle)
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('--idle', action='store_true', help='Run IMAP IDLE / persistent poller')
    parser.add_argument('--keepalive', type=int, default=300, help='Keepalive/NOOP interval in seconds (default 300)')
    parser.add_argument('--min-backoff', type=int, default=5, help='Minimum reconnect backoff seconds')
    parser.add_argument('--max-backoff', type=int, default=600, help='Maximum reconnect backoff seconds')
    args = parser.parse_args()

    def _connect_and_idle_loop(imap_cfg=None, keepalive=300, min_backoff=5, max_backoff=600):
        cfg = imap_cfg or IMAP
        host = cfg.get('HOST')
        port = cfg.get('PORT', 993)
        user = cfg.get('USER')
        password = cfg.get('PASSWORD')
        folder = cfg.get('FOLDER', 'INBOX')
        use_ssl = cfg.get('USE_SSL', True)

        backoff = min_backoff
        while True:
            conn = None
            try:
                logging.info('Conectando IMAP %s', host)
                if use_ssl:
                    conn = imaplib.IMAP4_SSL(host, port)
                else:
                    conn = imaplib.IMAP4(host, port)

                conn.login(user, password)
                conn.select(folder)

                # Si el servidor soporta IDLE, intentamos usarlo. Si falla, pasamos a un polling con NOOP.
                caps = getattr(conn, 'capabilities', []) or []
                caps = [c.decode() if isinstance(c, bytes) else c for c in caps]
                supports_idle = any('IDLE' in c.upper() for c in caps)

                if supports_idle:
                    logging.info('Servidor soporta IDLE — entrando en bucle IDLE (keepalive=%ss)', keepalive)
                    try:
                        sock = getattr(conn, 'sock', None)
                        if sock is None:
                            raise RuntimeError('No socket disponible para IDLE, fallback a polling')

                        while True:
                            try:
                                # Enviar comando IDLE
                                try:
                                    conn.send(b'IDLE\r\n')
                                except Exception:
                                    # algunos wrappers no exponen send; intentar usar socket
                                    sock.sendall(b'IDLE\r\n')

                                # Esperar datos con timeout keepalive
                                r, _, _ = select.select([sock], [], [], keepalive)
                                if r:
                                    data = sock.recv(4096)
                                    if not data:
                                        raise RuntimeError('Socket cerrado por servidor')
                                    text = data.decode(errors='ignore')
                                    # Si hay un EXISTS (nuevo mensaje), procesar
                                    if 'EXISTS' in text.upper() or 'RECENT' in text.upper():
                                        # Salir del IDLE enviando DONE
                                        try:
                                            sock.sendall(b'DONE\r\n')
                                        except Exception:
                                            pass
                                        # Buscar y procesar nuevos mensajes
                                        try:
                                            typ, data = conn.search(None, 'UNSEEN')
                                            if typ == 'OK':
                                                ids = data[0].split() if data and data[0] else []
                                                for _id in ids:
                                                    try:
                                                        typf, msg_data = conn.fetch(_id, '(RFC822)')
                                                        if typf != 'OK':
                                                            continue
                                                        raw = msg_data[0][1]
                                                        process_email_bytes(raw)
                                                        conn.store(_id, '+FLAGS', '\\Seen')
                                                    except Exception:
                                                        logging.exception('Falla procesando mensaje IMAP dentro de IDLE')
                                        except Exception:
                                            logging.exception('Error buscando mensajes UNSEEN')
                                        # volver a IDLE
                                        continue
                                    else:
                                        # Otros avisos — volver a IDLE
                                        continue
                                else:
                                    # keepalive expirado: mandar NOOP para mantener conexión
                                    try:
                                        conn.noop()
                                    except Exception:
                                        raise
                            except Exception:
                                logging.exception('Error en bucle IDLE — se reconectará')
                                break
                    except Exception:
                        logging.exception('Fallo intentando usar IDLE, caer a polling')

                # Fallback (o si no soporta IDLE): polling con NOOP/keepalive
                logging.info('Entrando en bucle de polling (keepalive=%ss)', keepalive)
                while True:
                    try:
                        # Buscar y procesar UNSEEN
                        typ, data = conn.search(None, 'UNSEEN')
                        if typ == 'OK':
                            ids = data[0].split() if data and data[0] else []
                            for _id in ids:
                                try:
                                    typf, msg_data = conn.fetch(_id, '(RFC822)')
                                    if typf != 'OK':
                                        continue
                                    raw = msg_data[0][1]
                                    process_email_bytes(raw)
                                    conn.store(_id, '+FLAGS', '\\Seen')
                                except Exception:
                                    logging.exception('Falla procesando mensaje IMAP en polling')
                        # Keepalive / NOOP
                        time.sleep(keepalive)
                        try:
                            conn.noop()
                        except Exception:
                            raise
                    except Exception:
                        logging.exception('Error en bucle de polling — se reconectará')
                        break

            except Exception:
                logging.exception('Error en conexión IMAP')
                # Reconexión con backoff exponencial
                logging.info('Reconectando en %s segundos...', backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            finally:
                try:
                    if conn:
                        try:
                            conn.logout()
                        except Exception:
                            conn.shutdown = True
                except Exception:
                    pass

    if args.idle:
        _connect_and_idle_loop(imap_cfg=None, keepalive=args.keepalive, min_backoff=args.min_backoff, max_backoff=args.max_backoff)
    else:
        out = poll_once()
        print(out)
