from flask import Blueprint, request, jsonify, current_app
import logging
import traceback as _traceback

from flask_app.services.email_service import EmailService, EmailParser
from flask_app.models.mensaje_model import MensajeModel
from flask_app.models.adjunto_model import AdjuntoModel
from flask_app.config.conexion_login import execute_query

inbound_bp = Blueprint('inbound', __name__)


def _extract_message_id_from_headers(headers_str):
    if not headers_str:
        return None
    try:
        for line in headers_str.splitlines():
            if line.lower().startswith('message-id:'):
                val = line.split(':', 1)[1].strip()
                return val.lstrip('<').rstrip('>').strip().lower()
    except Exception:
        logging.exception('Error parsing headers for Message-ID')
    return None


def _normalize_message_id(value):
    if not value:
        return None
    try:
        cleaned = str(value)
    except Exception:
        return None
    cleaned = cleaned.replace('\\r', '').replace('\\n', '')
    return cleaned.lstrip('<').rstrip('>').strip().lower()


@inbound_bp.route('/inbound/email', methods=['POST'])
def inbound_email():
    """Endpoint para recibir emails via webhook (SendGrid / Mailgun compatible).

    Acepta form-data o JSON. Valida la firma (si está configurada) y crea ticket/mensaje
    usando `MensajeModel.crear_desde_email`. Guarda adjuntos enviados como archivos.
    """
    try:
        raw_body = request.get_data() or b''
        # SendGrid/Twilio-SendGrid webhook headers
        signature = request.headers.get('X-Twilio-Email-Event-Webhook-Signature') or request.headers.get('X-SendGrid-Signature') or ''
        timestamp = request.headers.get('X-Twilio-Email-Event-Webhook-Timestamp') or request.headers.get('X-SendGrid-Timestamp') or ''

        # Validar webhook si está configurado
        try:
            if not EmailService.validar_webhook(raw_body, signature or '', timestamp or ''):
                return jsonify({'success': False, 'error': 'Invalid webhook signature'}), 403
        except Exception:
            logging.exception('Error validating webhook')

        # Extraer datos
        if request.is_json:
            payload = request.get_json() or {}
        else:
            payload = request.form.to_dict() or {}

        parsed = EmailParser.parse_sendgrid_webhook(payload)

        # Intentar obtener message-id desde headers o campos
        raw_headers = payload.get('headers') or payload.get('raw') or ''
        message_id = payload.get('message-id') or payload.get('Message-Id') or payload.get('message_id') or _extract_message_id_from_headers(raw_headers)
        message_id = _normalize_message_id(message_id)

        in_reply_to = payload.get('in-reply-to') or payload.get('in_reply_to') or payload.get('In-Reply-To')
        in_reply_to = _normalize_message_id(in_reply_to)

        email_data = {
            'from_email': parsed.get('from_email'),
            'from_name': parsed.get('from_name'),
            'subject': parsed.get('subject'),
            'body': parsed.get('body'),
            'id_depto': None,
            'id_canal': 1,
            'message_id': message_id,
            'in_reply_to': in_reply_to,
            'raw_headers': raw_headers,
        }

        # Detección temprana de duplicado por message_id
        if message_id:
            try:
                existing = execute_query("SELECT message_id, id_msg, id_ticket FROM email_message_ids WHERE message_id = %s", (message_id,), fetch_one=True)
                if existing:
                    logging.info('Webhook: mensaje duplicado message_id=%s, skipping', message_id)
                    return jsonify({'success': True, 'skipped': True, 'message_id': message_id, 'existing': existing}), 200
            except Exception:
                logging.exception('Error checking existing message_id')

        # Crear ticket/mensaje
        try:
            res = MensajeModel.crear_desde_email(email_data)
        except Exception as e:
            tb = _traceback.format_exc()
            logging.exception('Error creando desde webhook')
            # Devolver traceback temporalmente para depuración local
            return jsonify({'success': False, 'error': 'Error creating message', 'exc': str(e), 'trace': tb}), 500

        id_msg = res.get('id_msg')
        id_ticket = res.get('id_ticket')

        # Guardar adjuntos si vienen en files
        try:
            if request.files and id_ticket and id_msg:
                for key in request.files:
                    file = request.files.get(key)
                    if not file:
                        continue
                    filename = file.filename or 'adjunto'
                    ticket_dir = AdjuntoModel.obtener_ruta_por_ticket(id_ticket)
                    unique_name = AdjuntoModel.generar_nombre_unico(filename)
                    path = f"{ticket_dir}/{unique_name}"
                    try:
                        file.save(path)
                        AdjuntoModel.crear_adjunto({'nom_adj': filename, 'ruta': path, 'id_msg': id_msg})
                    except Exception:
                        logging.exception('Error saving webhook attachment')
        except Exception:
            logging.exception('Error processing webhook attachments')

        return jsonify({'success': True, 'id_msg': id_msg, 'id_ticket': id_ticket}), 200

    except Exception:
        logging.exception('Unhandled error in inbound webhook')
        return jsonify({'success': False, 'error': 'internal_error'}), 500
