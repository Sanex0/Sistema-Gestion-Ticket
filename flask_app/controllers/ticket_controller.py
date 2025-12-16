from flask import request, jsonify, Blueprint
from flask_app.models.ticket_model import TicketModel

ticket_bp = Blueprint('tickets', __name__)


@ticket_bp.route('/api/tickets/email', methods=['POST'])
def crear_ticket_desde_email():
    """
    Endpoint para recibir emails desde el agente y crear tickets.
    
    El agente debe enviar un POST con JSON:
    {
        "titulo": "Asunto del email",
        "es_ticket_externo": 1,
        "id_estado": 1,
        "id_prioridad": 2,
        "fecha_ini": "2025-12-15 10:30:00",
        "usuario_externo": {
            "nombre": "Juan Pérez",
            "email": "juan@example.com",
            "telefono": "+56912345678",
            "run": "12345678-9"
        },
        "mensaje": {
            "asunto": "Asunto del email",
            "contenido": "Cuerpo del email...",
            "remitente": "juan@example.com",
            "fecha_envio": "2025-12-15 10:30:00",
            "id_canal": 1
        }
    }
    """
    # Validar que venga JSON
    if not request.is_json:
        return jsonify({
            'success': False, 
            'error': 'Content-Type debe ser application/json'
        }), 400
    
    data = request.get_json()
    
    # Validaciones básicas
    if not data:
        return jsonify({
            'success': False, 
            'error': 'No se recibieron datos'
        }), 400
    
    if not data.get('usuario_externo', {}).get('email'):
        return jsonify({
            'success': False, 
            'error': 'El email del usuario es requerido'
        }), 400
    
    # Crear el ticket
    result = TicketModel.crear_ticket(data)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 500


@ticket_bp.route('/api/tickets', methods=['GET'])
def listar_tickets():
    """Obtiene la lista de tickets."""
    result = TicketModel.obtener_tickets()
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@ticket_bp.route('/api/tickets/<int:id_ticket>', methods=['GET'])
def obtener_ticket(id_ticket):
    """Obtiene un ticket específico por ID."""
    result = TicketModel.obtener_ticket_por_id(id_ticket)
    
    if result['success']:
        return jsonify(result), 200
    elif 'no encontrado' in result.get('error', '').lower():
        return jsonify(result), 404
    else:
        return jsonify(result), 500


@ticket_bp.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando."""
    return jsonify({
        'status': 'ok',
        'service': 'Ticket API - Club Recrear',
        'version': '1.0.0'
    }), 200


# ============================================
# ENDPOINTS PARA OPERADORES (SOLICITUDES)
# ============================================

@ticket_bp.route('/api/solicitudes', methods=['GET'])
def listar_solicitudes_pendientes():
    """
    Obtiene todas las solicitudes pendientes de aceptación.
    Son tickets nuevos (estado=1) sin operador asignado.
    """
    result = TicketModel.obtener_solicitudes_pendientes()
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@ticket_bp.route('/api/solicitudes/<int:id_ticket>/aceptar', methods=['POST'])
def aceptar_solicitud(id_ticket):
    """
    Acepta una solicitud y la asigna al operador.
    
    JSON esperado:
    {
        "id_operador": 1
    }
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type debe ser application/json'
        }), 400
    
    data = request.get_json()
    id_operador = data.get('id_operador')
    
    if not id_operador:
        return jsonify({
            'success': False,
            'error': 'id_operador es requerido'
        }), 400
    
    result = TicketModel.aceptar_solicitud(id_ticket, id_operador)
    
    if result['success']:
        return jsonify(result), 200
    elif 'no encontrado' in result.get('error', '').lower():
        return jsonify(result), 404
    elif 'ya fue aceptado' in result.get('error', '').lower():
        return jsonify(result), 409  # Conflict
    else:
        return jsonify(result), 500


@ticket_bp.route('/api/solicitudes/<int:id_ticket>/rechazar', methods=['POST'])
def rechazar_solicitud(id_ticket):
    """
    Rechaza una solicitud.
    
    JSON esperado:
    {
        "id_operador": 1,
        "motivo": "Razón del rechazo (opcional)"
    }
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type debe ser application/json'
        }), 400
    
    data = request.get_json()
    id_operador = data.get('id_operador')
    motivo = data.get('motivo')
    
    if not id_operador:
        return jsonify({
            'success': False,
            'error': 'id_operador es requerido'
        }), 400
    
    result = TicketModel.rechazar_solicitud(id_ticket, id_operador, motivo)
    
    if result['success']:
        return jsonify(result), 200
    elif 'no encontrado' in result.get('error', '').lower():
        return jsonify(result), 404
    else:
        return jsonify(result), 500


@ticket_bp.route('/api/operador/<int:id_operador>/tickets', methods=['GET'])
def listar_tickets_operador(id_operador):
    """
    Obtiene todos los tickets asignados a un operador.
    """
    result = TicketModel.obtener_tickets_operador(id_operador)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500