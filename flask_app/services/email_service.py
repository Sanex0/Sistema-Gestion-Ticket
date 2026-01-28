"""
Servicio de manejo de emails y webhooks de SendGrid
"""
import os
import hmac
import hashlib
from datetime import datetime
from email.utils import parseaddr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    """Servicio para manejo de emails vía SendGrid"""
    
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
    FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'soporte@tuempresa.com')
    WEBHOOK_KEY = os.getenv('SENDGRID_INBOUND_WEBHOOK_KEY', '')
    
    @staticmethod
    def enviar_email(to_email, subject, html_content, text_content=None):
        """
        Envía un email vía SendGrid
        
        Args:
            to_email: str - Email del destinatario
            subject: str - Asunto del email
            html_content: str - Contenido en HTML
            text_content: str - Contenido en texto plano (opcional)
        
        Returns:
            dict: {'success': bool, 'message_id': str}
        """
        try:
            if not EmailService.SENDGRID_API_KEY:
                return {
                    'success': False,
                    'error': 'SENDGRID_API_KEY no configurada'
                }
            
            message = Mail(
                from_email=EmailService.FROM_EMAIL,
                to_emails=to_email,
                subject=subject,
                plain_text_content=text_content or subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(EmailService.SENDGRID_API_KEY)
            response = sg.send(message)
            
            return {
                'success': True,
                'message_id': response.headers.get('X-Message-Id', 'desconocido')
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def notificar_nuevo_ticket(ticket_id, ticket_asunto, usuario_email):
        """
        Notifica al usuario que su ticket fue creado
        
        Args:
            ticket_id: int
            ticket_asunto: str
            usuario_email: str
        """
        html_content = f"""
        <h2>Ticket Creado Exitosamente</h2>
        <p>Hola,</p>
        <p>Tu ticket #{ticket_id} ha sido creado.</p>
        <p><strong>Asunto:</strong> {ticket_asunto}</p>
        <p>Un operador se pondrá en contacto pronto.</p>
        <p>ID del Ticket: {ticket_id}</p>
        """
        
        return EmailService.enviar_email(
            to_email=usuario_email,
            subject=f'Ticket #{ticket_id} - {ticket_asunto}',
            html_content=html_content
        )
    
    @staticmethod
    def notificar_respuesta_operador(ticket_id, operador_nombre, mensaje):
        """
        Notifica al usuario que hay una nueva respuesta en su ticket
        
        Args:
            ticket_id: int
            operador_nombre: str
            mensaje: str
        """
        html_content = f"""
        <h2>Nueva Respuesta en tu Ticket #{ticket_id}</h2>
        <p><strong>{operador_nombre}:</strong></p>
        <p>{mensaje}</p>
        """
        
        return html_content
    
    @staticmethod
    def validar_webhook(webhook_body, signature, timestamp):
        """
        Valida que el webhook viene de SendGrid (seguridad)
        
        Args:
            webhook_body: bytes - Cuerpo del webhook
            signature: str - Signature header de SendGrid
            timestamp: str - Timestamp header de SendGrid
        
        Returns:
            bool: True si es válido, False si no
        """
        if not EmailService.WEBHOOK_KEY:
            # Si no hay clave configurada, aceptar (desarrollo)
            return True
        
        try:
            # SendGrid usa HMAC-SHA256
            signed_content = f"{timestamp}{webhook_body.decode('utf-8')}"
            expected_signature = hmac.new(
                EmailService.WEBHOOK_KEY.encode(),
                signed_content.encode(),
                hashlib.sha256
            ).digest()
            
            # Comparar signatures
            return hmac.compare_digest(
                signature.encode(),
                expected_signature
            )
        except Exception as e:
            print(f"Error validando webhook: {e}")
            return False


class EmailParser:
    """Parser para emails recibidos vía SendGrid Inbound"""
    
    @staticmethod
    def parse_sendgrid_webhook(data):
        """
        Parsea datos del webhook de SendGrid Inbound Parse
        
        Args:
            data: dict - Datos del webhook (form-data)
        
        Returns:
            dict: {'from_email': str, 'from_name': str, 'subject': str, 'body': str}
        """
        raw_from = data.get('from', '')
        name, email_addr = parseaddr(raw_from)
        email_addr = (email_addr or '').strip().lower()
        name = (name or '').strip()
        return {
            'from_email': email_addr,
            'from_name': name or (email_addr.split('@')[0] if email_addr else 'Usuario'),
            'subject': data.get('subject', '[Sin asunto]'),
            'body': data.get('text') or data.get('html', ''),
            'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
            'sendgrid_event_id': data.get('sendgrid_event_id', '')
        }
