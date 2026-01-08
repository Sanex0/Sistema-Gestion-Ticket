from flask import Blueprint, jsonify, request

from flask_app.models.operador_model import OperadorModel
from flask_app.models.departamento_model import MiembroDptoModel
from flask_app.models.permiso_model import PermisoModel, RolPermisoModel, RolGlobalAdminModel
from flask_app.models.auditoria_model import AuditoriaModel
from flask_app.utils.error_handler import manejar_errores
from flask_app.utils.jwt_utils import token_requerido, rol_requerido
from flask_app.utils.error_handler import validar_campos_requeridos, ValidationError

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/usuarios', methods=['GET'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def listar_usuarios(operador_actual):
    """Lista todos los usuarios (operadores) del sistema. Solo Admin."""
    operadores = OperadorModel.listar_todos()

    usuarios = []
    for op in operadores or []:
        # Normalizar llaves según el cursor (dict o tuple)
        if isinstance(op, dict):
            operador_id = op.get('id') or op.get('id_operador')
            nombre = op.get('nombre')
            email = op.get('email')
            estado = op.get('estado')
            rol = op.get('rol_nombre') or op.get('rol_global')
        else:
            # Fallback defensivo (no debería ocurrir con DictCursor)
            operador_id, email, nombre, telefono, estado, rol_id, rol = op[:7]

        departamentos = op.get('departamentos') if isinstance(op, dict) else []

        usuarios.append({
            'id': operador_id,
            'nombre': nombre,
            'email': email,
            'rol': rol,
            'estado': estado,
            'ultimo_acceso': None,
            'departamentos': departamentos or []
        })

    return jsonify({'success': True, 'usuarios': usuarios}), 200


@admin_bp.route('/usuarios/<int:operador_id>', methods=['PATCH'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def actualizar_usuario(operador_actual, operador_id):
    """Edita un operador (rol/estado/datos) y opcionalmente asigna depto. Solo Admin."""
    data = request.get_json() or {}

    # Campos básicos requeridos para edición
    validar_campos_requeridos(data, ['email', 'nombre', 'id_rol_global', 'estado'])

    # Normalizar estado
    try:
        data['estado'] = int(data.get('estado'))
    except (TypeError, ValueError):
        raise ValidationError('estado inválido')

    # Actualizar operador (local + externa)
    OperadorModel.actualizar_admin(operador_id, data)

    # Asignación opcional de depto
    depto_id = data.get('depto_id')
    depto_rol = data.get('depto_rol')
    if depto_id:
        try:
            depto_id = int(depto_id)
        except (TypeError, ValueError):
            raise ValidationError('depto_id inválido')

        if depto_rol not in ['Agente', 'Supervisor', 'Jefe']:
            raise ValidationError('depto_rol inválido (Agente|Supervisor|Jefe)')

        MiembroDptoModel.asignar_miembro({
            'id_operador': operador_id,
            'id_depto': depto_id,
            'rol': depto_rol
        })

    return jsonify({'success': True, 'message': 'Usuario actualizado'}), 200


@admin_bp.route('/permisos', methods=['GET'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def listar_permisos(operador_actual):
    """Lista el catálogo de permisos activos. Solo Admin."""
    permisos = PermisoModel.listar_activos() or []
    return jsonify({'success': True, 'data': permisos}), 200


@admin_bp.route('/roles', methods=['GET'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def listar_roles_con_permisos(operador_actual):
    """Lista roles globales con sus permisos asignados (dinámico). Solo Admin."""
    solo_activos = request.args.get('solo_activos', '1') != '0'
    roles = RolPermisoModel.listar_roles_con_permisos(solo_activos=solo_activos)
    return jsonify({'success': True, 'data': roles}), 200


@admin_bp.route('/roles', methods=['POST'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def crear_rol(operador_actual):
    """Crea un rol global y asigna permisos. Solo Admin."""
    data = request.get_json() or {}

    validar_campos_requeridos(data, ['nombre'])

    nombre = data.get('nombre')
    activo = data.get('activo', 1)
    permiso_ids = data.get('permiso_ids') or []

    rol_id = RolGlobalAdminModel.crear(nombre=nombre, activo=activo)
    RolPermisoModel.reemplazar_permisos(rol_id, permiso_ids)

    return jsonify({'success': True, 'data': {'id': rol_id}}), 201


@admin_bp.route('/roles/<int:rol_id>/permisos', methods=['PUT'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def reemplazar_permisos_rol(operador_actual, rol_id):
    """Reemplaza la lista de permisos asignados a un rol. Solo Admin."""
    data = request.get_json() or {}

    permiso_ids = data.get('permiso_ids')
    if permiso_ids is None:
        raise ValidationError('permiso_ids requerido')

    RolPermisoModel.reemplazar_permisos(rol_id, permiso_ids)
    return jsonify({'success': True, 'message': 'Permisos actualizados'}), 200


@admin_bp.route('/roles/<int:rol_id>', methods=['PATCH'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def actualizar_rol(operador_actual, rol_id):
    """Edita un rol global (nombre/activo) y opcionalmente sus permisos. Solo Admin."""
    data = request.get_json() or {}

    nombre = data.get('nombre') if 'nombre' in data else None
    activo = data.get('activo') if 'activo' in data else None

    RolGlobalAdminModel.actualizar(rol_id, nombre=nombre, activo=activo)

    if 'permiso_ids' in data:
        permiso_ids = data.get('permiso_ids')
        if permiso_ids is None:
            raise ValidationError('permiso_ids inválido')
        RolPermisoModel.reemplazar_permisos(rol_id, permiso_ids)

    return jsonify({'success': True, 'message': 'Rol actualizado'}), 200


@admin_bp.route('/auditoria', methods=['GET'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def listar_auditoria(operador_actual):
    """Lista auditoría (filtrable). Solo Admin."""
    depto_id = request.args.get('depto_id', type=int)
    operador_id = request.args.get('operador_id', type=int)
    accion = request.args.get('accion')
    fecha = request.args.get('fecha')
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)

    data = AuditoriaModel.listar(
        depto_id=depto_id,
        operador_id=operador_id,
        accion=accion,
        fecha=fecha,
        limit=min(max(limit, 1), 200),
        offset=max(offset, 0)
    )

    return jsonify({'success': True, 'data': data}), 200


@admin_bp.route('/auditoria/acciones', methods=['GET'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def listar_acciones_auditoria(operador_actual):
    """Lista acciones distintas disponibles para un departamento (para poblar filtros)."""
    depto_id = request.args.get('depto_id', type=int)
    operador_id = request.args.get('operador_id', type=int)

    if not depto_id and not operador_id:
        return jsonify({'success': True, 'data': []}), 200

    acciones = AuditoriaModel.listar_acciones_distintas(depto_id, operador_id=operador_id)
    return jsonify({'success': True, 'data': acciones}), 200
