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
    
    GET /api/operadores
    
    Response:
    {
        "success": true,
        "data": [...]
    }
    """
    operadores = OperadorModel.listar_todos()
    
    return jsonify({
        'success': True,
        'data': operadores
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
