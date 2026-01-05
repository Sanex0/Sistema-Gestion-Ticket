"""
Controller para endpoints de catálogos del sistema
Estados, Prioridades, Clubes, SLAs, Roles, Canales
"""
from flask import Blueprint, jsonify
from flask_app.models.estado_model import EstadoModel
from flask_app.models.prioridad_model import PrioridadModel
from flask_app.models.club_model import ClubModel
from flask_app.models.sla_model import SLAModel
from flask_app.models.operador_model import RolGlobalModel
from flask_app.utils.jwt_utils import token_requerido
from flask_app.utils.error_handler import manejar_errores

catalogo_bp = Blueprint('catalogos', __name__, url_prefix='/api/catalogos')


@catalogo_bp.route('/estados', methods=['GET'])
@token_requerido
@manejar_errores
def listar_estados(operador_actual):
    """
    Listar todos los estados de tickets
    
    GET /api/catalogos/estados
    
    Response:
    {
        "success": true,
        "estados": [
            {"id": 1, "descripcion": "Nuevo"},
            {"id": 2, "descripcion": "En Proceso"}
        ]
    }
    """
    estados = EstadoModel.listar()
    
    return jsonify({
        'success': True,
        'data': estados,
        'total': len(estados) if estados else 0
    }), 200


@catalogo_bp.route('/prioridades', methods=['GET'])
@token_requerido
@manejar_errores
def listar_prioridades(operador_actual):
    """
    Listar todas las prioridades
    
    GET /api/catalogos/prioridades
    
    Response:
    {
        "success": true,
        "prioridades": [
            {"id": 1, "descripcion": "Urgente", "jerarquia": 1},
            {"id": 2, "descripcion": "Alta", "jerarquia": 2}
        ]
    }
    """
    prioridades = PrioridadModel.listar()
    
    return jsonify({
        'success': True,
        'data': prioridades,
        'total': len(prioridades) if prioridades else 0
    }), 200


@catalogo_bp.route('/clubes', methods=['GET'])
@token_requerido
@manejar_errores
def listar_clubes(operador_actual):
    """
    Listar todos los clubes
    
    GET /api/catalogos/clubes
    
    Response:
    {
        "success": true,
        "clubes": [
            {"id": 1, "nombre": "Club Central"},
            {"id": 2, "nombre": "Club Norte"}
        ]
    }
    """
    clubes = ClubModel.listar()
    
    return jsonify({
        'success': True,
        'data': clubes,
        'total': len(clubes) if clubes else 0
    }), 200


@catalogo_bp.route('/slas', methods=['GET'])
@token_requerido
@manejar_errores
def listar_slas(operador_actual):
    """
    Listar todos los SLAs activos
    
    GET /api/catalogos/slas
    
    Response:
    {
        "success": true,
        "slas": [
            {
                "id": 1,
                "nombre": "SLA Estándar",
                "tiempo_primera_respuesta_min": 60,
                "tiempo_resolucion_min": 480,
                "activo": 1
            }
        ]
    }
    """
    slas = SLAModel.listar()
    
    return jsonify({
        'success': True,
        'data': slas,
        'total': len(slas) if slas else 0
    }), 200


@catalogo_bp.route('/roles', methods=['GET'])
@token_requerido
@manejar_errores
def listar_roles(operador_actual):
    """
    Listar todos los roles globales
    
    GET /api/catalogos/roles
    
    Response:
    {
        "success": true,
        "roles": [
            {"id": 1, "nombre": "Admin", "activo": 1},
            {"id": 2, "nombre": "Supervisor", "activo": 1}
        ]
    }
    """
    roles = RolGlobalModel.listar()
    
    return jsonify({
        'success': True,
        'data': roles,
        'total': len(roles) if roles else 0
    }), 200


@catalogo_bp.route('/canales', methods=['GET'])
@token_requerido
@manejar_errores
def listar_canales(operador_actual):
    """
    Listar todos los canales de comunicación
    
    GET /api/catalogos/canales
    
    Response:
    {
        "success": true,
        "canales": [
            {"id": 1, "nombre": "Email"},
            {"id": 2, "nombre": "Web"}
        ]
    }
    """
    from flask_app.config.conexion_login import get_local_db_connection
    
    conn = get_local_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id_canal as id, nombre FROM canal ORDER BY id_canal")
    canales = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'data': canales,
        'total': len(canales) if canales else 0
    }), 200
