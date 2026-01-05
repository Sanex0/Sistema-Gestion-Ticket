from flask import Blueprint, request, jsonify
from flask_app.models.etiqueta_model import EtiquetaModel
from flask_app.utils.jwt_utils import token_requerido, rol_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, ValidationError, NotFoundError

etiqueta_bp = Blueprint('etiqueta', __name__, url_prefix='/api/etiquetas')


@etiqueta_bp.route('', methods=['GET'])
@manejar_errores
def listar_etiquetas():
    """
    Lista todas las etiquetas.
    
    GET /api/etiquetas
    
    Response:
    {
        "success": true,
        "etiquetas": [...],
        "total": 10
    }
    """
    etiquetas = EtiquetaModel.listar()
    
    return jsonify({
        'success': True,
        'etiquetas': etiquetas,
        'total': len(etiquetas)
    }), 200


@etiqueta_bp.route('/<int:etiqueta_id>', methods=['GET'])
@manejar_errores
def obtener_etiqueta(etiqueta_id):
    """
    Obtiene una etiqueta por ID.
    
    GET /api/etiquetas/{etiqueta_id}
    
    Response:
    {
        "success": true,
        "etiqueta": {...}
    }
    """
    etiqueta = EtiquetaModel.buscar_por_id(etiqueta_id)
    
    if not etiqueta:
        raise NotFoundError(f"Etiqueta con ID {etiqueta_id} no encontrada")
    
    return jsonify({
        'success': True,
        'etiqueta': etiqueta
    }), 200


@etiqueta_bp.route('', methods=['POST'])
@token_requerido
@rol_requerido(['Admin', 'Supervisor'])
@manejar_errores
def crear_etiqueta(operador_actual):
    """
    Crea una nueva etiqueta.
    
    POST /api/etiquetas
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "nombre": "Urgente",
        "color": "#FF0000"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Etiqueta creada exitosamente",
        "id_etiqueta": 1
    }
    """
    data = request.get_json()
    
    validar_campos_requeridos(data, ['nombre'])
    
    # Validar color si viene
    if 'color' in data:
        if not EtiquetaModel.validar_color(data['color']):
            raise ValidationError("Color inválido. Debe ser formato hexadecimal (#RRGGBB)")
    
    # Verificar que no exista con ese nombre
    existe = EtiquetaModel.buscar_por_nombre(data['nombre'])
    if existe:
        raise ValidationError(f"Ya existe una etiqueta con el nombre '{data['nombre']}'")
    
    resultado = EtiquetaModel.crear_etiqueta(data)
    
    return jsonify({
        'success': True,
        'mensaje': 'Etiqueta creada exitosamente',
        'id_etiqueta': resultado['id_etiqueta']
    }), 201


@etiqueta_bp.route('/<int:etiqueta_id>', methods=['PUT', 'PATCH'])
@token_requerido
@rol_requerido(['Admin', 'Supervisor'])
@manejar_errores
def actualizar_etiqueta(etiqueta_id, operador_actual):
    """
    Actualiza una etiqueta.
    
    PUT/PATCH /api/etiquetas/{etiqueta_id}
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "nombre": "Nuevo nombre",
        "color": "#00FF00"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Etiqueta actualizada exitosamente"
    }
    """
    data = request.get_json()
    
    # Verificar que existe
    etiqueta = EtiquetaModel.buscar_por_id(etiqueta_id)
    if not etiqueta:
        raise NotFoundError(f"Etiqueta con ID {etiqueta_id} no encontrada")
    
    # Validar color si viene
    if 'color' in data:
        if not EtiquetaModel.validar_color(data['color']):
            raise ValidationError("Color inválido. Debe ser formato hexadecimal (#RRGGBB)")
    
    # Si cambia el nombre, verificar que no exista
    if 'nombre' in data and data['nombre'] != etiqueta['nombre']:
        existe = EtiquetaModel.buscar_por_nombre(data['nombre'])
        if existe:
            raise ValidationError(f"Ya existe una etiqueta con el nombre '{data['nombre']}'")
    
    EtiquetaModel.actualizar_etiqueta(etiqueta_id, data)
    
    return jsonify({
        'success': True,
        'mensaje': 'Etiqueta actualizada exitosamente'
    }), 200


@etiqueta_bp.route('/<int:etiqueta_id>', methods=['DELETE'])
@token_requerido
@rol_requerido(['Admin'])
@manejar_errores
def eliminar_etiqueta(etiqueta_id, operador_actual):
    """
    Elimina una etiqueta y sus asociaciones.
    
    DELETE /api/etiquetas/{etiqueta_id}
    Headers:
        - Authorization: Bearer {token}
    
    Response:
    {
        "success": true,
        "mensaje": "Etiqueta eliminada exitosamente"
    }
    """
    # Verificar que existe
    etiqueta = EtiquetaModel.buscar_por_id(etiqueta_id)
    if not etiqueta:
        raise NotFoundError(f"Etiqueta con ID {etiqueta_id} no encontrada")
    
    EtiquetaModel.eliminar_etiqueta(etiqueta_id)
    
    return jsonify({
        'success': True,
        'mensaje': 'Etiqueta eliminada exitosamente'
    }), 200


@etiqueta_bp.route('/<int:etiqueta_id>/tickets', methods=['GET'])
@manejar_errores
def listar_tickets_etiqueta(etiqueta_id):
    """
    Lista los tickets que tienen una etiqueta.
    
    GET /api/etiquetas/{etiqueta_id}/tickets
    
    Response:
    {
        "success": true,
        "tickets": [...],
        "total": 15
    }
    """
    tickets = EtiquetaModel.listar_tickets_por_etiqueta(etiqueta_id)
    
    return jsonify({
        'success': True,
        'tickets': tickets,
        'total': len(tickets)
    }), 200


# ========== ENDPOINTS DE ASIGNACIÓN ==========

@etiqueta_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@manejar_errores
def listar_etiquetas_ticket(ticket_id):
    """
    Lista las etiquetas de un ticket.
    
    GET /api/etiquetas/tickets/{ticket_id}
    
    Response:
    {
        "success": true,
        "etiquetas": [...],
        "total": 3
    }
    """
    etiquetas = EtiquetaModel.listar_por_ticket(ticket_id)
    
    return jsonify({
        'success': True,
        'etiquetas': etiquetas,
        'total': len(etiquetas)
    }), 200


@etiqueta_bp.route('/tickets/<int:ticket_id>', methods=['POST'])
@token_requerido
@manejar_errores
def asignar_etiqueta_ticket(ticket_id, operador_actual):
    """
    Asigna una etiqueta a un ticket.
    
    POST /api/etiquetas/tickets/{ticket_id}
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "id_etiqueta": 1
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Etiqueta asignada al ticket"
    }
    """
    data = request.get_json()
    
    validar_campos_requeridos(data, ['id_etiqueta'])
    
    # Verificar que la etiqueta existe
    etiqueta = EtiquetaModel.buscar_por_id(data['id_etiqueta'])
    if not etiqueta:
        raise NotFoundError(f"Etiqueta con ID {data['id_etiqueta']} no encontrada")
    
    EtiquetaModel.asignar_a_ticket(ticket_id, data['id_etiqueta'])
    
    return jsonify({
        'success': True,
        'mensaje': 'Etiqueta asignada al ticket'
    }), 200


@etiqueta_bp.route('/tickets/<int:ticket_id>/<int:etiqueta_id>', methods=['DELETE'])
@token_requerido
@manejar_errores
def desasignar_etiqueta_ticket(ticket_id, etiqueta_id, operador_actual):
    """
    Desasigna una etiqueta de un ticket.
    
    DELETE /api/etiquetas/tickets/{ticket_id}/{etiqueta_id}
    Headers:
        - Authorization: Bearer {token}
    
    Response:
    {
        "success": true,
        "mensaje": "Etiqueta desasignada del ticket"
    }
    """
    EtiquetaModel.desasignar_de_ticket(ticket_id, etiqueta_id)
    
    return jsonify({
        'success': True,
        'mensaje': 'Etiqueta desasignada del ticket'
    }), 200


@etiqueta_bp.route('/tickets/<int:ticket_id>/bulk', methods=['PUT'])
@token_requerido
@manejar_errores
def reemplazar_etiquetas_ticket(ticket_id, operador_actual):
    """
    Reemplaza todas las etiquetas de un ticket.
    
    PUT /api/etiquetas/tickets/{ticket_id}/bulk
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "etiquetas": [1, 2, 3]
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Etiquetas actualizadas exitosamente"
    }
    """
    data = request.get_json()
    
    validar_campos_requeridos(data, ['etiquetas'])
    
    if not isinstance(data['etiquetas'], list):
        raise ValidationError("El campo 'etiquetas' debe ser una lista de IDs")
    
    # Verificar que todas las etiquetas existen
    for id_etiqueta in data['etiquetas']:
        etiqueta = EtiquetaModel.buscar_por_id(id_etiqueta)
        if not etiqueta:
            raise NotFoundError(f"Etiqueta con ID {id_etiqueta} no encontrada")
    
    EtiquetaModel.reemplazar_etiquetas_ticket(ticket_id, data['etiquetas'])
    
    return jsonify({
        'success': True,
        'mensaje': 'Etiquetas actualizadas exitosamente'
    }), 200
