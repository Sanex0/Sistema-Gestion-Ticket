from flask import request, jsonify, Blueprint
from flask_app.models.ticket_model import TicketModel
from flask_app.models.estado_model import EstadoModel
from flask_app.models.prioridad_model import PrioridadModel
from flask_app.models.club_model import ClubModel
from flask_app.models.sla_model import SLAModel
from flask_app.utils.jwt_utils import token_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, NotFoundError, ValidationError

ticket_bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')


# ============================================
# ENDPOINTS PUBLICOS (sin autenticacion)
# ============================================

@ticket_bp.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API esta funcionando."""
    return jsonify({
        'status': 'ok',
        'service': 'Ticket API - Sistema de Tickets',
        'version': '2.0.0'
    }), 200


@ticket_bp.route('', methods=['GET'])
@token_requerido
@manejar_errores
def listar_tickets(operador_actual):
    """
    Lista tickets según permisos del operador autenticado.
    
    GET /api/tickets?limit=20&offset=0
    
    Filtrado:
    - Operador: Solo ve sus tickets asignados
    - Supervisor: Ve sus tickets + de subordinados
    - Admin: Ve todos
    
    Query params:
        - limit: Limite de resultados (default: 50)
        - offset: Offset para paginacion (default: 0)
    """
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    # Pasar el operador_actual para filtrado
    result = TicketModel.get_all(limit=limit, offset=offset, operador_actual=operador_actual)
    
    if result.get('success'):
        return jsonify({
            'success': True,
            'tickets': result['tickets'],
            'total': result['total'],
            'limit': limit,
            'offset': offset
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Error al obtener tickets')
        }), 500


@ticket_bp.route('/<int:ticket_id>', methods=['GET'])
@manejar_errores
def obtener_ticket(ticket_id):
    """
    Obtiene un ticket especifico con detalles completos y mensajes.
    
    GET /api/tickets/{ticket_id}
    """
    result = TicketModel.get_by_id(ticket_id)
    
    if not result.get('success'):
        return jsonify({
            'success': False,
            'error': result.get('error', 'Ticket no encontrado')
        }), 404
    
    return jsonify({
        'success': True,
        'ticket': result['ticket']
    }), 200



# ============================================
# ENDPOINTS PROTEGIDOS (requieren autenticacion)
# ============================================

@ticket_bp.route('', methods=['POST'])
@token_requerido
@manejar_errores
def crear_ticket_protegido(operador_actual):
    """
    Crea un nuevo ticket (requiere autenticacion).
    
    POST /api/tickets
    Headers:
        Authorization: Bearer <token>
    Body:
    {
        "titulo": "Titulo del ticket",
        "tipo_ticket": "Publico",
        "descripcion": "Descripcion del problema",
        "id_estado": 1,
        "id_prioridad": 2,
        "id_club": 1,
        "id_sla": 1,
        "usuario_externo": {
            "nombre": "Juan Perez",
            "email": "juan@example.com",
            "telefono": "+56912345678",
            "rut": "12345678-9"
        }
    }
    """
    data = request.get_json()
    
    # Validar campos requeridos
    validar_campos_requeridos(data, [
        'titulo', 'tipo_ticket', 'id_estado', 'id_prioridad', 
        'id_club', 'id_sla'
    ])
    
    result = TicketModel.crear(data, operador_actual=operador_actual)
    
    if result.get('success'):
        return jsonify({
            'success': True,
            'id_ticket': result['id_ticket'],
            'message': 'Ticket creado exitosamente'
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Error al crear ticket')
        }), 400


@ticket_bp.route('/<int:ticket_id>', methods=['PUT', 'PATCH'])
@token_requerido
@manejar_errores
def actualizar_ticket_protegido(operador_actual, ticket_id):
    """
    Actualiza los datos de un ticket (requiere autenticacion).
    
    PUT/PATCH /api/tickets/{ticket_id}
    Headers:
        Authorization: Bearer <token>
    Body:
    {
        "titulo": "Nuevo titulo",
        "descripcion": "Nueva descripcion",
        "id_estado": 2,
        "id_prioridad": 3
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'No se proporcionaron datos para actualizar'
        }), 400
    
    # Por ahora, solo retornar que no esta implementado
    return jsonify({
        'success': False,
        'error': 'Actualizacion de tickets aun no implementada',
        'ticket_id': ticket_id
    }), 501
