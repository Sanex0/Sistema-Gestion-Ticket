from flask import Blueprint, request, jsonify
from flask_app.models.operador_model import OperadorModel, RolGlobalModel
from flask_app.utils.jwt_utils import token_requerido, rol_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, ValidationError, NotFoundError

operador_bp = Blueprint('operador', __name__, url_prefix='/api/operadores')


@operador_bp.route('', methods=['GET'])
@token_requerido
@manejar_errores
def listar_operadores(operador_actual):
    """
    Lista todos los operadores del sistema.
    Opcionalmente puede filtrar por departamento.
    
    GET /api/operadores
    GET /api/operadores?id_depto=1
    
    Response:
    {
        "success": true,
        "operadores": [...]
    }
    """
    id_depto = request.args.get('id_depto', type=int)
    
    if id_depto:
        # Filtrar operadores por departamento
        operadores = OperadorModel.listar_por_departamento(id_depto)
    else:
        # Listar todos
        operadores = OperadorModel.listar_todos()
    
    return jsonify({
        'success': True,
        'operadores': operadores
    }), 200


@operador_bp.route('/<int:operador_id>', methods=['GET'])
@token_requerido
@manejar_errores
def obtener_operador(operador_actual, operador_id):
    """
    Obtiene un operador por ID.
    
    GET /api/operadores/{operador_id}
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    operador = OperadorModel.buscar_por_id(operador_id)
    
    if not operador:
        raise NotFoundError(f"Operador con ID {operador_id} no encontrado")
    
    return jsonify({
        'success': True,
        'data': operador
    }), 200


@operador_bp.route('/me', methods=['GET'])
@token_requerido
@manejar_errores
def obtener_mi_perfil(operador_actual):
    """
    Obtiene el perfil completo del operador autenticado.
    Incluye sus departamentos y roles en cada uno.
    
    GET /api/operadores/me
    
    Response:
    {
        "success": true,
        "operador": {
            "id": 1,
            "nombre": "Juan Pérez",
            "email": "juan@email.com",
            "rol_global": "Agente",
            "departamentos": [
                {"id_depto": 1, "departamento_nombre": "Soporte", "rol_departamento": "Supervisor"},
                {"id_depto": 2, "departamento_nombre": "Ventas", "rol_departamento": "Agente"}
            ],
            "es_supervisor": true,
            "es_admin": false
        }
    }
    """
    perfil = OperadorModel.obtener_perfil_completo(operador_actual['operador_id'])
    
    if not perfil:
        raise NotFoundError("No se pudo obtener el perfil del operador")
    
    return jsonify({
        'success': True,
        'operador': perfil
    }), 200


@operador_bp.route('/me', methods=['PATCH'])
@token_requerido
@manejar_errores
def actualizar_mi_perfil(operador_actual):
    """Actualiza el perfil del operador autenticado (nombre, email, telefono)."""
    data = request.get_json() or {}

    # Llamar al modelo para actualizar
    OperadorModel.actualizar_perfil(operador_actual['operador_id'], data)

    # Devolver el perfil actualizado
    perfil = OperadorModel.obtener_perfil_completo(operador_actual['operador_id'])
    return jsonify({
        'success': True,
        'operador': perfil
    }), 200


@operador_bp.route('/roles', methods=['GET'])
@token_requerido
@manejar_errores
def listar_roles(operador_actual):
    """
    Lista todos los roles activos.
    
    GET /api/operadores/roles
    
    Response:
    {
        "success": true,
        "data": [...]
    }
    """
    roles = RolGlobalModel.listar_activos()
    
    return jsonify({
        'success': True,
        'data': roles
    }), 200
