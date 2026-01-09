from flask import request, jsonify, Blueprint
from flask_app.models.ticket_model import TicketModel
from flask_app.models.estado_model import EstadoModel
from flask_app.models.prioridad_model import PrioridadModel
from flask_app.models.club_model import ClubModel
from flask_app.models.sla_model import SLAModel
from flask_app.utils.jwt_utils import token_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, NotFoundError, ValidationError
from datetime import datetime, timedelta
import logging

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


@ticket_bp.route('/estadisticas', methods=['GET'])
@token_requerido
@manejar_errores
def obtener_estadisticas(operador_actual):
    """Obtiene estadísticas/KPIs visibles según permisos del operador."""
    result = TicketModel.get_estadisticas(operador_actual=operador_actual)

    if result.get('success'):
        return jsonify({
            'success': True,
            'estadisticas': result['estadisticas']
        }), 200

    return jsonify({
        'success': False,
        'error': result.get('error', 'Error al obtener estadísticas')
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
            'id_msg_inicial': result.get('id_msg_inicial'),
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

@ticket_bp.route('/<int:ticket_id>/estado', methods=['PATCH'])
@token_requerido
@manejar_errores
def cambiar_estado(operador_actual, ticket_id):
    """
    Cambia el estado de un ticket con validaciones de reglas de negocio.
    
    PATCH /api/tickets/{ticket_id}/estado
    Headers:
        Authorization: Bearer <token>
    Body:
    {
        "id_estado": 2
    }
    
    Reglas:
    - Solo el Receptor/Owner puede marcar como "Resuelto" (3)
    - Solo el Emisor puede "Cerrar" (4) cuando desee
    - Si está "Cerrado" (4), solo el Emisor puede reabrirlo
    - Estado "Nuevo" (1) debe permanecer al menos 1 hora (excepto cierre por emisor/admin)
    """
    data = request.get_json()
    validar_campos_requeridos(data, ['id_estado'])
    
    nuevo_estado_id = data['id_estado']
    
    # Obtener ticket actual
    ticket_result = TicketModel.get_by_id(ticket_id)
    if not ticket_result.get('success'):
        raise NotFoundError(f'Ticket #{ticket_id} no encontrado')
    
    ticket = ticket_result['ticket']
    estado_actual_id = ticket['id_estado']

    # Identidad/roles
    id_operador_actual = (
        operador_actual.get('operador_id')
        or operador_actual.get('id_operador')
        or operador_actual.get('id')
    )
    if not id_operador_actual:
        raise ValidationError('Operador no identificado')

    rol_id = operador_actual.get('rol_id') or operador_actual.get('id_rol_global')
    rol_nombre = operador_actual.get('rol') or operador_actual.get('rol_nombre')
    is_admin = (rol_id == 1) or (isinstance(rol_nombre, str) and rol_nombre.lower() == 'admin')

    id_emisor = ticket.get('id_operador_emisor')
    # En get_by_id, el Owner viene en la key 'id_operador'
    id_owner = ticket.get('id_operador')

    es_emisor = id_emisor is not None and str(id_emisor) == str(id_operador_actual)
    es_owner = id_owner is not None and str(id_owner) == str(id_operador_actual)

    # ==============================
    # REGLAS DE NEGOCIO: ESTADOS
    # ==============================
    # Admin: sin restricciones adicionales
    if not is_admin:
        nuevo_estado_int = int(nuevo_estado_id)
        estado_actual_int = int(estado_actual_id)

        # Resuelto (3): solo receptor/Owner
        if nuevo_estado_int == 3 and not es_owner:
            raise ValidationError('Solo el receptor (Owner) del ticket puede marcarlo como Resuelto')

        # Cerrado (4): solo emisor
        if nuevo_estado_int == 4 and not es_emisor:
            raise ValidationError('Solo el emisor del ticket puede cerrarlo')

        # Si el ticket está cerrado, solo el emisor puede reabrirlo
        if estado_actual_int == 4 and nuevo_estado_int != 4 and not es_emisor:
            raise ValidationError('Solo el emisor del ticket puede reabrir un ticket cerrado')

        # Receptor/Owner (si NO es emisor): solo puede cambiar a Resuelto
        if es_owner and not es_emisor and nuevo_estado_int != 3:
            raise ValidationError('El receptor solo puede marcar el ticket como Resuelto')

        # Emisor (si NO es owner): solo puede Cerrar, o Reabrir si está cerrado
        if es_emisor and not es_owner:
            if estado_actual_int != 4 and nuevo_estado_int != 4:
                raise ValidationError('El emisor solo puede cerrar el ticket (o reabrirlo si está cerrado)')
            if estado_actual_int == 4 and nuevo_estado_int == 3:
                raise ValidationError('Solo el receptor (Owner) del ticket puede marcarlo como Resuelto')
    
    # REGLA: Estado "Nuevo" debe permanecer al menos 1 hora
    if estado_actual_id == 1 and nuevo_estado_id != 1:  # Intentando salir de "Nuevo"
        fecha_creacion = ticket['fecha_ini']
        if isinstance(fecha_creacion, str):
            fecha_creacion = datetime.strptime(fecha_creacion, '%Y-%m-%d %H:%M:%S')
        
        tiempo_transcurrido = datetime.now() - fecha_creacion
        
        # Si no ha pasado 1 hora, solo permitir cambio si hay respuesta (se maneja en mensaje_controller)
        # Excepción: el emisor (o admin) puede cerrar cuando desee.
        if tiempo_transcurrido < timedelta(hours=1):
            if int(nuevo_estado_id) == 4 and (is_admin or es_emisor):
                pass
            else:
                # Verificar si tiene mensajes (respuestas)
                from flask_app.models.mensaje_model import MensajeModel
                mensajes = MensajeModel.listar_por_ticket(ticket_id, incluir_privados=False)

                # Si no tiene mensajes y quiere cambiar estado, rechazar
                if not mensajes or len(mensajes) == 0:
                    minutos_restantes = int((timedelta(hours=1) - tiempo_transcurrido).total_seconds() / 60)
                    raise ValidationError(
                        f'El ticket debe permanecer en estado "Nuevo" al menos 1 hora. '
                        f'Tiempo restante: {minutos_restantes} minutos'
                    )
    
    # REGLA 3: Validar que el nuevo estado existe
    estado = EstadoModel.buscar_por_id(nuevo_estado_id)
    if not estado:
        raise NotFoundError(f'Estado con ID {nuevo_estado_id} no encontrado')
    
    # Actualizar estado
    result = TicketModel.cambiar_estado(ticket_id, nuevo_estado_id, id_operador_actual)
    
    if result:
        return jsonify({
            'success': True,
            'message': f'Estado cambiado a: {estado["descripcion"]}',
            'ticket_id': ticket_id,
            'nuevo_estado': {
                'id': nuevo_estado_id,
                'nombre': estado['descripcion']
            }
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Error al cambiar el estado del ticket'
        }), 500


@ticket_bp.route('/<int:ticket_id>/prioridad', methods=['PATCH'])
@token_requerido
@manejar_errores
def cambiar_prioridad(operador_actual, ticket_id):
    """
    Cambia la prioridad de un ticket.
    
    PATCH /api/tickets/{ticket_id}/prioridad
    Headers:
        Authorization: Bearer <token>
    Body:
    {
        "id_prioridad": 1
    }
    """
    data = request.get_json()
    validar_campos_requeridos(data, ['id_prioridad'])
    
    nueva_prioridad_id = data['id_prioridad']
    
    # Obtener ticket actual
    ticket_result = TicketModel.get_by_id(ticket_id)
    if not ticket_result.get('success'):
        raise NotFoundError(f'Ticket #{ticket_id} no encontrado')
    
    ticket = ticket_result['ticket']
    
    # Validar que el ticket no esté cerrado
    if ticket['id_estado'] == 4:  # Cerrado
        raise ValidationError('No se puede cambiar la prioridad de un ticket cerrado')
    
    # Validar que la nueva prioridad existe
    prioridad = PrioridadModel.buscar_por_id(nueva_prioridad_id)
    if not prioridad:
        raise NotFoundError(f'Prioridad con ID {nueva_prioridad_id} no encontrada')
    
    # Actualizar prioridad
    result = TicketModel.cambiar_prioridad(ticket_id, nueva_prioridad_id, operador_actual['operador_id'])
    
    if result:
        return jsonify({
            'success': True,
            'message': f'Prioridad cambiada a: {prioridad["descripcion"]}',
            'ticket_id': ticket_id,
            'nueva_prioridad': {
                'id': nueva_prioridad_id,
                'nombre': prioridad['descripcion'],
                'jerarquia': prioridad['jerarquia']
            }
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Error al cambiar la prioridad del ticket'
        }), 500

@ticket_bp.route('/actualizar-estados-automaticos', methods=['POST'])
@token_requerido
@manejar_errores
def actualizar_estados_automaticos(operador_actual):
    pass


@ticket_bp.route('/<int:ticket_id>/historial', methods=['GET'])
@manejar_errores
def obtener_historial_ticket(ticket_id):
    """
    Obtiene el historial de acciones de un ticket
    """
    from flask_app.models.ticket_model import TicketModel
    
    try:
        historial = TicketModel.obtener_historial_ticket(ticket_id)
        
        if historial is None:
            return jsonify({
                'success': False,
                'error': 'No se pudo obtener el historial del ticket'
            }), 500
        
        return jsonify({
            'success': True,
            'data': historial
        }), 200
        
    except Exception as e:
        logger.error(f"Error al obtener historial del ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ticket_bp.route('/emisores', methods=['GET'])
@token_requerido
@manejar_errores
def listar_emisores(operador_actual):
    """
    Lista emisores únicos según el contexto del operador.
    
    - Admin: Todos los emisores
    - Supervisor: Emisores que han enviado tickets a sus departamentos
    - Agente: Emisores que le han enviado tickets a él
    
    GET /api/tickets/emisores
    """
    result = TicketModel.get_emisores_por_contexto(operador_actual)
    
    if result.get('success'):
        return jsonify({
            'success': True,
            'emisores': result['emisores']
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Error al obtener emisores')
        }), 500


@ticket_bp.route('/receptores', methods=['GET'])
@token_requerido
@manejar_errores
def listar_receptores(operador_actual):
    """
    Lista receptores (owners) únicos según el contexto del operador.
    
    - Admin: Todos los receptores
    - Supervisor: Receptores de sus departamentos
    - Agente: Solo él mismo
    
    GET /api/tickets/receptores
    """
    result = TicketModel.get_receptores_por_contexto(operador_actual)
    
    if result.get('success'):
        return jsonify({
            'success': True,
            'receptores': result['receptores']
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Error al obtener receptores')
        }), 500


@ticket_bp.route('/<int:id_ticket>/tomar', methods=['POST'])
@token_requerido
@manejar_errores
def tomar_ticket(operador_actual, id_ticket):
    """
    Permite a un operador tomar (auto-asignarse) un ticket sin asignar.
    Solo puede tomar tickets de su departamento.
    
    POST /api/tickets/<id_ticket>/tomar
    
    Returns:
        200: Ticket tomado exitosamente
        400: Ticket ya asignado o sin permisos
        500: Error del servidor
    """
    result = TicketModel.tomar_ticket(id_ticket, operador_actual)
    
    if result.get('success'):
        return jsonify({
            'success': True,
            'message': result['message'],
            'id_ticket': result['id_ticket']
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Error al tomar ticket')
        }), 400


@ticket_bp.route('/<int:id_ticket>/asignar', methods=['POST'])
@token_requerido
@manejar_errores
def asignar_ticket_endpoint(operador_actual, id_ticket):
    """
    Permite a un supervisor/admin asignar un ticket a otro operador.
    
    POST /api/tickets/<id_ticket>/asignar
    Body: {"id_operador": 123}
    
    Returns:
        200: Ticket asignado exitosamente
        400: Permisos insuficientes o error de validación
        500: Error del servidor
    """
    data = request.get_json()
    
    if not data or 'id_operador' not in data:
        return jsonify({
            'success': False,
            'error': 'Se requiere el campo id_operador'
        }), 400
    
    id_operador_nuevo = data['id_operador']
    
    result = TicketModel.asignar_ticket(id_ticket, id_operador_nuevo, operador_actual)
    
    if result.get('success'):
        return jsonify({
            'success': True,
            'message': result['message'],
            'id_ticket': result['id_ticket'],
            'operador_asignado': result.get('operador_asignado')
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Error al asignar ticket')
        }), 400


@ticket_bp.route('/respuestas-rapidas', methods=['GET'])
@token_requerido
@manejar_errores
def obtener_respuestas_rapidas(operador_actual):
    """
    Obtiene las respuestas rápidas del operador actual
    Incluye respuestas estándar del sistema y personales del operador
    """
    from flask_app.models.respuesta_rapida_model import RespuestaRapidaModel
    
    try:
        id_operador = operador_actual['operador_id']
        respuestas = RespuestaRapidaModel.obtener_por_operador(id_operador)
        
        return jsonify({
            'success': True,
            'data': respuestas,
            'total': len(respuestas)
        }), 200
        
    except Exception as e:
        logging.error(f"Error al obtener respuestas rápidas: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
