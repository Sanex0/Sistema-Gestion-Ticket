from flask import Blueprint, request, jsonify
from flask_app.models.departamento_model import DepartamentoModel, MiembroDptoModel
from flask_app.utils.jwt_utils import token_requerido, rol_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, ValidationError, NotFoundError

departamento_bp = Blueprint('departamento', __name__, url_prefix='/api/departamentos')


@departamento_bp.route('', methods=['GET'])
@manejar_errores
def listar_departamentos():
    """
    Lista todos los departamentos.
    
    GET /api/departamentos
    Query params:
        - incluir_no_externos: bool (default: true)
    
    Response:
    {
        "success": true,
        "departamentos": [...],
        "total": 5
    }
    """
    incluir_no_externos = request.args.get('incluir_no_externos', 'true').lower() == 'true'
    
    departamentos = DepartamentoModel.listar(incluir_no_externos)
    
    return jsonify({
        'success': True,
        'departamentos': departamentos,
        'total': len(departamentos)
    }), 200


@departamento_bp.route('/<int:depto_id>', methods=['GET'])
@manejar_errores
def obtener_departamento(depto_id):
    """
    Obtiene un departamento por ID.
    
    GET /api/departamentos/{depto_id}
    
    Response:
    {
        "success": true,
        "departamento": {...}
    }
    """
    departamento = DepartamentoModel.buscar_por_id(depto_id)
    
    if not departamento:
        raise NotFoundError(f"Departamento con ID {depto_id} no encontrado")
    
    return jsonify({
        'success': True,
        'departamento': departamento
    }), 200


@departamento_bp.route('', methods=['POST'])
@token_requerido
@rol_requerido(['Admin', 'Supervisor'])
@manejar_errores
def crear_departamento(operador_actual):
    """
    Crea un nuevo departamento.
    
    POST /api/departamentos
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "descripcion": "Soporte Técnico",
        "email": "soporte@empresa.com",
        "operador_default": 1,
        "recibe_externo": true
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Departamento creado exitosamente",
        "id_depto": 1
    }
    """
    data = request.get_json()
    
    validar_campos_requeridos(data, ['descripcion', 'email', 'operador_default'])
    
    resultado = DepartamentoModel.crear_departamento(data)
    
    return jsonify({
        'success': True,
        'mensaje': 'Departamento creado exitosamente',
        'id_depto': resultado['id_depto']
    }), 201


@departamento_bp.route('/<int:depto_id>', methods=['PUT', 'PATCH'])
@token_requerido
@rol_requerido(['Admin', 'Supervisor'])
@manejar_errores
def actualizar_departamento(depto_id, operador_actual):
    """
    Actualiza un departamento.
    
    PUT/PATCH /api/departamentos/{depto_id}
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "descripcion": "Nuevo nombre",
        "email": "nuevo@email.com",
        "operador_default": 2,
        "recibe_externo": false
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Departamento actualizado exitosamente"
    }
    """
    data = request.get_json()
    
    # Verificar que existe
    departamento = DepartamentoModel.buscar_por_id(depto_id)
    if not departamento:
        raise NotFoundError(f"Departamento con ID {depto_id} no encontrado")
    
    DepartamentoModel.actualizar_departamento(depto_id, data)
    
    return jsonify({
        'success': True,
        'mensaje': 'Departamento actualizado exitosamente'
    }), 200


@departamento_bp.route('/<int:depto_id>', methods=['DELETE'])
@token_requerido
@rol_requerido(['Admin'])
@manejar_errores
def eliminar_departamento(depto_id, operador_actual):
    """
    Elimina un departamento.
    Solo si no tiene miembros activos.
    
    DELETE /api/departamentos/{depto_id}
    Headers:
        - Authorization: Bearer {token}
    
    Response:
    {
        "success": true,
        "mensaje": "Departamento eliminado exitosamente"
    }
    """
    success, mensaje = DepartamentoModel.eliminar_departamento(depto_id)
    
    if not success:
        raise ValidationError(mensaje)
    
    return jsonify({
        'success': True,
        'mensaje': mensaje
    }), 200


# ========== ENDPOINTS DE MIEMBROS ==========

@departamento_bp.route('/<int:depto_id>/miembros', methods=['GET'])
@manejar_errores
def listar_miembros(depto_id):
    """
    Lista los miembros de un departamento.
    
    GET /api/departamentos/{depto_id}/miembros
    Query params:
        - solo_activos: bool (default: true)
    
    Response:
    {
        "success": true,
        "miembros": [...],
        "total": 5
    }
    """
    solo_activos = request.args.get('solo_activos', 'true').lower() == 'true'
    
    miembros = MiembroDptoModel.listar_por_departamento(depto_id, solo_activos)
    
    return jsonify({
        'success': True,
        'miembros': miembros,
        'total': len(miembros)
    }), 200


@departamento_bp.route('/<int:depto_id>/miembros', methods=['POST'])
@token_requerido
@rol_requerido(['Admin', 'Supervisor'])
@manejar_errores
def asignar_miembro(depto_id, operador_actual):
    """
    Asigna un operador al departamento.
    
    POST /api/departamentos/{depto_id}/miembros
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "id_operador": 1,
        "rol": "Agente|Supervisor|Jefe"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Miembro asignado exitosamente"
    }
    """
    data = request.get_json()
    
    validar_campos_requeridos(data, ['id_operador', 'rol'])
    
    # Validar rol
    if data['rol'] not in ['Agente', 'Supervisor', 'Jefe']:
        raise ValidationError("El rol debe ser: Agente, Supervisor o Jefe")
    
    data['id_depto'] = depto_id
    MiembroDptoModel.asignar_miembro(data)
    
    return jsonify({
        'success': True,
        'mensaje': 'Miembro asignado exitosamente'
    }), 201


@departamento_bp.route('/<int:depto_id>/miembros/<int:operador_id>', methods=['DELETE'])
@token_requerido
@rol_requerido(['Admin', 'Supervisor'])
@manejar_errores
def desasignar_miembro(depto_id, operador_id, operador_actual):
    """
    Desasigna un operador del departamento.
    
    DELETE /api/departamentos/{depto_id}/miembros/{operador_id}
    Headers:
        - Authorization: Bearer {token}
    
    Response:
    {
        "success": true,
        "mensaje": "Miembro desasignado exitosamente"
    }
    """
    MiembroDptoModel.desasignar_miembro(operador_id, depto_id)
    
    return jsonify({
        'success': True,
        'mensaje': 'Miembro desasignado exitosamente'
    }), 200


@departamento_bp.route('/<int:depto_id>/miembros/<int:operador_id>/rol', methods=['PATCH'])
@token_requerido
@rol_requerido(['Admin', 'Supervisor'])
@manejar_errores
def cambiar_rol_miembro(depto_id, operador_id, operador_actual):
    """
    Cambia el rol de un miembro en el departamento.
    
    PATCH /api/departamentos/{depto_id}/miembros/{operador_id}/rol
    Headers:
        - Authorization: Bearer {token}
    Body:
    {
        "rol": "Supervisor"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Rol actualizado exitosamente"
    }
    """
    data = request.get_json()
    
    validar_campos_requeridos(data, ['rol'])
    
    if data['rol'] not in ['Agente', 'Supervisor', 'Jefe']:
        raise ValidationError("El rol debe ser: Agente, Supervisor o Jefe")
    
    MiembroDptoModel.cambiar_rol(operador_id, depto_id, data['rol'])
    
    return jsonify({
        'success': True,
        'mensaje': 'Rol actualizado exitosamente'
    }), 200


@departamento_bp.route('/<int:depto_id>/jefes', methods=['GET'])
@manejar_errores
def obtener_jefes(depto_id):
    """
    Obtiene los jefes de un departamento.
    
    GET /api/departamentos/{depto_id}/jefes
    
    Response:
    {
        "success": true,
        "jefes": [...],
        "total": 2
    }
    """
    jefes = MiembroDptoModel.obtener_jefes_departamento(depto_id)
    
    return jsonify({
        'success': True,
        'jefes': jefes,
        'total': len(jefes)
    }), 200


@departamento_bp.route('/operador/<int:operador_id>', methods=['GET'])
@manejar_errores
def listar_departamentos_operador(operador_id):
    """
    Lista los departamentos de un operador.
    
    GET /api/departamentos/operador/{operador_id}
    Query params:
        - solo_activos: bool (default: true)
    
    Response:
    {
        "success": true,
        "departamentos": [...],
        "total": 3
    }
    """
    solo_activos = request.args.get('solo_activos', 'true').lower() == 'true'
    
    departamentos = MiembroDptoModel.listar_por_operador(operador_id, solo_activos)
    
    return jsonify({
        'success': True,
        'departamentos': departamentos,
        'total': len(departamentos)
    }), 200
