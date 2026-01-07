from flask import Blueprint, request, jsonify

from flask_app.models.notificacion_model import NotificacionModel
from flask_app.utils.jwt_utils import token_requerido
from flask_app.utils.error_handler import manejar_errores, ValidationError


notificacion_bp = Blueprint('notificaciones', __name__, url_prefix='/api/notificaciones')


@notificacion_bp.route('', methods=['GET'])
@token_requerido
@manejar_errores
def listar_notificaciones(operador_actual):
    """Lista notificaciones del operador autenticado."""
    id_operador = operador_actual.get('operador_id')
    if not id_operador:
        raise ValidationError('Operador inválido')

    unread = request.args.get('unread', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))

    result = NotificacionModel.listar_por_operador(
        id_operador=id_operador,
        solo_no_leidas=unread,
        limit=limit,
        offset=offset,
    )

    unread_count = NotificacionModel.contar_no_leidas(id_operador)

    return jsonify({
        'success': True,
        'notificaciones': result['notificaciones'],
        'total': result['total'],
        'unread_count': unread_count,
        'limit': limit,
        'offset': offset,
    }), 200


@notificacion_bp.route('/resumen', methods=['GET'])
@token_requerido
@manejar_errores
def resumen_notificaciones(operador_actual):
    """Devuelve contadores de notificaciones del operador autenticado."""
    id_operador = operador_actual.get('operador_id')
    if not id_operador:
        raise ValidationError('Operador inválido')

    unread_count = NotificacionModel.contar_no_leidas(id_operador)

    return jsonify({
        'success': True,
        'unread_count': unread_count,
    }), 200


@notificacion_bp.route('/<int:id_notificacion>/leer', methods=['POST'])
@token_requerido
@manejar_errores
def marcar_leida(id_notificacion, operador_actual):
    """Marca una notificación como leída (solo si pertenece al operador)."""
    id_operador = operador_actual.get('operador_id')
    if not id_operador:
        raise ValidationError('Operador inválido')

    NotificacionModel.marcar_leida(id_notificacion, id_operador)
    unread_count = NotificacionModel.contar_no_leidas(id_operador)

    return jsonify({
        'success': True,
        'unread_count': unread_count,
    }), 200


@notificacion_bp.route('/leer-todas', methods=['POST'])
@token_requerido
@manejar_errores
def marcar_todas_leidas(operador_actual):
    """Marca todas las notificaciones del operador como leídas."""
    id_operador = operador_actual.get('operador_id')
    if not id_operador:
        raise ValidationError('Operador inválido')

    NotificacionModel.marcar_todas_leidas(id_operador)

    return jsonify({
        'success': True,
        'unread_count': 0,
    }), 200
