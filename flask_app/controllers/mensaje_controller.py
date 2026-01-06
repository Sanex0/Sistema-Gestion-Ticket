from flask import Blueprint, request, jsonify
from flask_app.models.mensaje_model import MensajeModel
from flask_app.models.ticket_model import TicketModel
from flask_app.utils.jwt_utils import token_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, ValidationError, NotFoundError

mensaje_bp = Blueprint('mensaje', __name__, url_prefix='/api')


@mensaje_bp.route('/tickets/<int:ticket_id>/mensajes', methods=['GET'])
@token_requerido
def listar_mensajes(operador_actual, ticket_id):
    """
    Lista todos los mensajes de un ticket.
    
    GET /api/tickets/{ticket_id}/mensajes
    """
    try:
        print(f"📩 [API] Obteniendo mensajes del ticket #{ticket_id}")
        
        # Validar acceso del operador al ticket
        if not TicketModel.operador_puede_ver_ticket(ticket_id, operador_actual):
            return jsonify({
                'success': False,
                'error': 'Permiso denegado'
            }), 403

        incluir_privados = request.args.get('incluir_privados', 'false').lower() == 'true'
        tipo_usuario = 'Operador'
        
        # Llamar al modelo
        mensajes_raw = MensajeModel.listar_por_ticket(ticket_id, incluir_privados, tipo_usuario)
        
        print(f"✅ [API] Se encontraron {len(mensajes_raw) if mensajes_raw else 0} mensajes para ticket #{ticket_id}")
        
        # Convertir a lista de diccionarios simples
        mensajes = []
        if mensajes_raw:
            for msg in mensajes_raw:
                # Verificar que el mensaje pertenece al ticket correcto
                if msg.get('id_ticket') != ticket_id:
                    print(f"⚠️ [API] ERROR: Mensaje {msg.get('id_msg')} pertenece al ticket #{msg.get('id_ticket')}, no al #{ticket_id}")
                    continue
                
                msg_dict = {
                    'id_msg': msg.get('id_msg'),
                    'id_ticket': msg.get('id_ticket'),
                    'tipo_mensaje': msg.get('tipo_mensaje'),
                    'asunto': msg.get('asunto'),
                    'contenido': msg.get('contenido'),
                    'remitente_id': msg.get('remitente_id'),
                    'remitente_tipo': msg.get('remitente_tipo'),
                    'remitente_nombre': msg.get('remitente_nombre'),
                    'remitente_email': msg.get('remitente_email'),
                    'estado_mensaje': msg.get('estado_mensaje'),
                    'canal_nombre': msg.get('canal_nombre'),
                    'id_canal': msg.get('id_canal'),
                    'total_adjuntos': msg.get('total_adjuntos'),
                    'fecha_envio': str(msg.get('fecha_envio')) if msg.get('fecha_envio') else None,
                    'fecha_edicion': str(msg.get('fecha_edicion')) if msg.get('fecha_edicion') else None
                }
                mensajes.append(msg_dict)
        
        return jsonify({
            'success': True,
            'data': mensajes,
            'total': len(mensajes)
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mensaje_bp.route('/tickets/<int:ticket_id>/mensajes/chat', methods=['GET'])
@manejar_errores
def obtener_chat(ticket_id):
    """
    Obtiene mensajes formateados para chat.
    
    GET /api/tickets/{ticket_id}/mensajes/chat
    Headers (opcional):
        - Authorization: Bearer {token} - Si es operador, ve mensajes privados
    
    Response:
    {
        "success": true,
        "mensajes": [
            {
                "id": 1,
                "autor": "Juan Pérez",
                "tipo_autor": "Usuario",
                "mensaje": "Contenido del mensaje",
                "fecha": "2025-12-29T10:30:00",
                "editado": false,
                "es_privado": false,
                "canal": "Email",
                "adjuntos": 2
            }
        ]
    }
    """
    # Verificar si hay token de operador
    auth_header = request.headers.get('Authorization')
    id_operador = None
    
    if auth_header and auth_header.startswith('Bearer '):
        # Aquí podrías decodificar el token para obtener el id_operador
        # Por ahora, simplemente marcamos que es un operador
        id_operador = 1  # Placeholder
    
    mensajes = MensajeModel.obtener_para_chat(ticket_id, id_operador)
    
    return jsonify({
        'success': True,
        'mensajes': mensajes,
        'total': len(mensajes)
    }), 200


@mensaje_bp.route('/mensajes', methods=['POST'])
@manejar_errores
@token_requerido
def crear_mensaje(operador_actual):
    """
    Crea un nuevo mensaje en un ticket (endpoint simplificado).
    
    POST /api/mensajes
    Body:
    {
        "id_ticket": 1,
        "contenido": "Texto del mensaje",
        "id_canal": 2,  // Opcional (default: 2=Web)
        "es_interno": false  // Opcional (default: false)
    }
    """
    
    data = request.get_json()
    
    # Validar campos requeridos
    validar_campos_requeridos(data, ['id_ticket', 'contenido'])
    
    # Preparar datos para el modelo
    mensaje_data = {
        'tipo_mensaje': 'Privado' if data.get('es_interno', False) else 'Publico',
        'asunto': 'Respuesta',
        'contenido': data['contenido'],
        'remitente_id': operador_actual['operador_id'],
        'remitente_tipo': 'Operador',
        'id_ticket': data['id_ticket'],
        'id_canal': data.get('id_canal', 2)
    }
    
    # Validar reglas de escritura en ticket
    ticket_id = data['id_ticket']
    if not TicketModel.operador_puede_escribir_ticket(ticket_id, operador_actual):
        # Mensaje claro para UI
        ticket_info = TicketModel.get_acl_info(ticket_id)
        if ticket_info and ticket_info.get('id_estado') == 4:
            raise ValidationError('El ticket está cerrado. No se pueden enviar más mensajes.')
        raise ValidationError('Debes tomar el ticket (o ser el responsable) para responder.')

    resultado = MensajeModel.crear_mensaje(mensaje_data)
    
    # REGLA DE NEGOCIO: Si el ticket recibe una respuesta, cambiar automáticamente a "En Proceso"
    ticket_result = TicketModel.get_by_id(ticket_id)
    
    if ticket_result.get('success'):
        ticket = ticket_result['ticket']
        estado_actual = ticket['id_estado']
        
        # Si está en "Nuevo" (1) y recibe una respuesta, cambiar a "En Proceso" (2)
        if estado_actual == 1:
            TicketModel.cambiar_estado(
                ticket_id=ticket_id,
                nuevo_estado_id=2,  # En Proceso
                operador_id=operador_actual['operador_id']
            )
            print(f"✅ Ticket #{ticket_id} cambió automáticamente de 'Nuevo' a 'En Proceso'")
    
    # Obtener el mensaje completo para retornarlo
    mensaje_completo = MensajeModel.buscar_por_id(resultado['id_msg'])
    
    return jsonify({
        'success': True,
        'mensaje': 'Mensaje enviado correctamente',
        'data': {
            'id_msg': mensaje_completo['id_msg'],
            'id_ticket': mensaje_completo['id_ticket'],
            'contenido': mensaje_completo['contenido'],
            'fecha_creacion': mensaje_completo['fecha_creacion'].isoformat() if mensaje_completo.get('fecha_creacion') else None,
            'remitente_nombre': mensaje_completo.get('remitente_nombre'),
            'tipo_mensaje': mensaje_completo.get('tipo_mensaje')
        }
    }), 201


@mensaje_bp.route('/mensajes/<int:mensaje_id>', methods=['GET'])
@manejar_errores
def obtener_mensaje(mensaje_id):
    """
    Obtiene un mensaje por su ID.
    
    GET /api/mensajes/{mensaje_id}
    
    Response:
    {
        "success": true,
        "mensaje": {...}
    }
    """
    mensaje = MensajeModel.buscar_por_id(mensaje_id)
    
    if not mensaje:
        raise NotFoundError(f"Mensaje con ID {mensaje_id} no encontrado")
    
    return jsonify({
        'success': True,
        'mensaje': mensaje
    }), 200


@mensaje_bp.route('/mensajes/<int:mensaje_id>', methods=['PUT', 'PATCH'])
@token_requerido
@manejar_errores
def actualizar_mensaje(mensaje_id, operador_actual):
    """
    Actualiza el contenido de un mensaje.
    
    PUT/PATCH /api/mensajes/{mensaje_id}
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "contenido": "Nuevo contenido"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Mensaje actualizado exitosamente"
    }
    """
    data = request.get_json()
    
    # Validar campos requeridos
    validar_campos_requeridos(data, ['contenido'])
    
    # Verificar que el mensaje existe
    mensaje = MensajeModel.buscar_por_id(mensaje_id)
    if not mensaje:
        raise NotFoundError(f"Mensaje con ID {mensaje_id} no encontrado")
    
    # Solo el remitente o un admin puede editar
    # TODO: Implementar validación de permisos
    
    MensajeModel.actualizar_mensaje(mensaje_id, data)
    
    return jsonify({
        'success': True,
        'mensaje': 'Mensaje actualizado exitosamente'
    }), 200


@mensaje_bp.route('/mensajes/<int:mensaje_id>', methods=['DELETE'])
@token_requerido
@manejar_errores
def eliminar_mensaje(mensaje_id, operador_actual):
    """
    Elimina un mensaje (soft delete).
    
    DELETE /api/mensajes/{mensaje_id}
    Headers:
        - Authorization: Bearer {token}
    Query params:
        - permanente: bool (default: false) - Eliminar permanentemente
    
    Response:
    {
        "success": true,
        "mensaje": "Mensaje eliminado exitosamente"
    }
    """
    # Verificar que el mensaje existe
    mensaje = MensajeModel.buscar_por_id(mensaje_id)
    if not mensaje:
        raise NotFoundError(f"Mensaje con ID {mensaje_id} no encontrado")
    
    permanente = request.args.get('permanente', 'false').lower() == 'true'
    
    # Solo admin puede eliminar permanentemente
    if permanente and operador_actual.get('rol') != 'Admin':
        raise ValidationError("Solo los administradores pueden eliminar mensajes permanentemente")
    
    MensajeModel.eliminar_mensaje(mensaje_id, soft_delete=not permanente)
    
    return jsonify({
        'success': True,
        'mensaje': 'Mensaje eliminado exitosamente'
    }), 200


@mensaje_bp.route('/mensajes/<int:mensaje_id>/interno', methods=['PATCH'])
@token_requerido
@manejar_errores
def marcar_interno(mensaje_id, operador_actual):
    """
    Marca un mensaje como interno (privado).
    Solo operadores pueden ver mensajes internos.
    
    PATCH /api/mensajes/{mensaje_id}/interno
    Headers:
        - Authorization: Bearer {token}
    
    Response:
    {
        "success": true,
        "mensaje": "Mensaje marcado como interno"
    }
    """
    # Verificar que el mensaje existe
    mensaje = MensajeModel.buscar_por_id(mensaje_id)
    if not mensaje:
        raise NotFoundError(f"Mensaje con ID {mensaje_id} no encontrado")
    
    MensajeModel.marcar_como_interno(mensaje_id)
    
    return jsonify({
        'success': True,
        'mensaje': 'Mensaje marcado como interno'
    }), 200


@mensaje_bp.route('/mensajes/email', methods=['POST'])
@manejar_errores
def recibir_email():
    """
    Endpoint público para recibir emails y crear mensajes/tickets.
    Soporta webhooks de SendGrid Inbound Parse y requests JSON.
    
    POST /api/mensajes/email
    
    Desde SendGrid (form-data):
    - from: "usuario@example.com"
    - subject: "Asunto del email"
    - text/html: "Contenido del email"
    
    O JSON:
    {
        "from_email": "usuario@example.com",
        "from_name": "Usuario Nombre",
        "subject": "Asunto del email",
        "body": "Contenido del email",
        "ticket_id": 123  // Opcional
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Email procesado exitosamente",
        "id_msg": 1,
        "id_ticket": 1
    }
    """
    from flask_app.services.email_service import EmailParser, EmailService
    
    try:
        # Detectar si es JSON o form-data (SendGrid)
        if request.is_json:
            data = request.get_json()
        else:
            # Parsear SendGrid Inbound Parse webhook
            data = EmailParser.parse_sendgrid_webhook(request.form.to_dict())
            
            # Validar webhook (opcional en desarrollo)
            timestamp = request.headers.get('X-Twilio-Email-Event-Webhook-Timestamp', '')
            signature = request.headers.get('X-Twilio-Email-Event-Webhook-Signature', '')
            
            if timestamp and signature:
                is_valid = EmailService.validar_webhook(
                    request.get_data(),
                    signature,
                    timestamp
                )
                if not is_valid:
                    return jsonify({
                        'success': False,
                        'error': 'Webhook signature inválida'
                    }), 401
        
        # Validar campos requeridos
        validar_campos_requeridos(data, ['from_email', 'subject', 'body'])
        
        # Crear mensaje/ticket desde email
        resultado = MensajeModel.crear_desde_email(data)
        
        return jsonify({
            'success': True,
            'mensaje': 'Email procesado exitosamente',
            'id_msg': resultado['id_msg'],
            'id_ticket': resultado['id_ticket']
        }), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
