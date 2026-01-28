from flask import Blueprint, request, jsonify
from flask_app.models.operador_model import OperadorModel, RolGlobalModel
from flask_app.utils.jwt_utils import generar_token, token_requerido, rol_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, ValidationError, AuthenticationError, AuthorizationError
from flask_app.config.conexion_login import get_db_connection
import bcrypt

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
@manejar_errores
def login():
    """
    Endpoint para autenticación de operadores.
    
    POST /api/auth/login
    Body:
    {
        "email": "operador@ejemplo.com",
        "password": "contraseña"
    }
    
    Response:
    {
        "success": true,
        "access_token": "...",
        "refresh_token": "...",
        "operador": {
            "id": 1,
            "nombre": "Juan Pérez",
            "email": "operador@ejemplo.com",
            "rol": "Agente"
        }
    }
    """
    data = request.get_json()
    
    # Validar campos requeridos
    validar_campos_requeridos(data, ['email', 'password'])
    
    email = data['email']
    password = data['password']
    
    # Buscar operador en la tabla local (sistema_ticket_recrear)
    operador = OperadorModel.buscar_por_email(email)
    
    if not operador:
        raise AuthenticationError(
            'Email incorrecto',
            payload={'error_code': 'INVALID_EMAIL'}
        )
    
    # Verificar que el operador esté activo
    if operador['estado'] != 1:
        raise AuthorizationError(
            'Usuario inactivo. Contacte al administrador',
            payload={'error_code': 'INACTIVE_USER'}
        )
    
    # Validar contraseña contra la base de datos externa (adrecrear_usuarios)
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT clave_usuario, estado_usuario FROM adrecrear_usuarios WHERE email_usuario=%s",
            (email,)
        )
        user = cursor.fetchone()
        
        if not user:
            raise AuthenticationError(
                'Email incorrecto',
                payload={'error_code': 'INVALID_EMAIL'}
            )
        
        # `get_db_connection()` devuelve cursores con DictCursor, por eso `user` es un dict.
        # Acceder por claves en vez de índices numéricos.
        estado_usuario = int(user.get('estado_usuario') or 0)
        if estado_usuario != 1:
            raise AuthorizationError(
                'Usuario inactivo. Contacte al administrador',
                payload={'error_code': 'INACTIVE_USER'}
            )

        # Verificar contraseña con bcrypt
        hashed_raw = user.get('clave_usuario')
        if not hashed_raw:
            raise AuthenticationError(
                'Contraseña incorrecta',
                payload={'error_code': 'INVALID_PASSWORD'}
            )

        hashed_password = hashed_raw.encode('utf-8')
        if not bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            raise AuthenticationError(
                'Contraseña incorrecta',
                payload={'error_code': 'INVALID_PASSWORD'}
            )
            
    except AuthenticationError:
        # Re-lanzar errores de autenticación
        raise
    except AuthorizationError:
        # Re-lanzar errores de autorización
        raise
    except Exception as e:
        print(f"Error en validación de contraseña: {str(e)}")
        raise AuthenticationError(
            'Error al validar credenciales',
            payload={'error_code': 'AUTH_ERROR'}
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    # Generar tokens
    access_token = generar_token(
        operador['id'],
        operador['email'],
        operador['rol_nombre'],
        tipo='access'
    )
    
    refresh_token = generar_token(
        operador['id'],
        operador['email'],
        operador['rol_nombre'],
        tipo='refresh'
    )
    
    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'operador': {
            'id': operador['id'],
            'nombre': operador['nombre'],
            'email': operador['email'],
            'rol': operador['rol_nombre']
        }
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@manejar_errores
def refresh():
    """
    Endpoint para refrescar el token de acceso usando un refresh token.
    
    POST /api/auth/refresh
    Body:
    {
        "refresh_token": "..."
    }
    
    Response:
    {
        "success": true,
        "access_token": "..."
    }
    """
    from flask_app.utils.jwt_utils import verificar_token
    
    data = request.get_json()
    
    validar_campos_requeridos(data, ['refresh_token'])
    
    # Verificar refresh token
    payload = verificar_token(data['refresh_token'])
    
    if not payload or 'error' in payload:
        raise AuthenticationError('Refresh token inválido o expirado')
    
    if payload.get('tipo') != 'refresh':
        raise AuthenticationError('Token inválido. Se requiere un refresh token.')
    
    # Verificar que el operador aún exista y esté activo
    operador = OperadorModel.buscar_por_id(payload['operador_id'])
    
    if not operador or operador['estado'] != 1:
        raise AuthenticationError('Usuario no encontrado o inactivo')
    
    # Generar nuevo access token
    access_token = generar_token(
        operador['id'],
        operador['email'],
        operador['rol_nombre'],
        tipo='access'
    )
    
    return jsonify({
        'success': True,
        'access_token': access_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_requerido
@manejar_errores
def obtener_perfil(operador_actual):
    """
    Endpoint para obtener información del operador autenticado.
    
    GET /api/auth/me
    Headers:
        Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "operador": {
            "id": 1,
            "nombre": "Juan Pérez",
            "email": "operador@ejemplo.com",
            "telefono": "+56912345678",
            "rol": "Agente",
            "estado": 1
        }
    }
    """
    operador_id = operador_actual['operador_id']
    
    operador = OperadorModel.buscar_por_id(operador_id)
    
    if not operador:
        raise AuthenticationError('Operador no encontrado')
    
    return jsonify({
        'success': True,
        'operador': {
            'id': operador['id'],
            'nombre': operador['nombre'],
            'email': operador['email'],
            'telefono': operador['telefono'],
            'rol': operador['rol_nombre'],
            'estado': operador['estado']
        }
    }), 200


@auth_bp.route('/registro', methods=['POST'])
@token_requerido
@rol_requerido('Admin')
@manejar_errores
def registrar_operador(operador_actual):
    """
    Endpoint para registrar un nuevo operador (solo Admin).
    
    POST /api/auth/registro
    Headers:
        Authorization: Bearer <token>
    Body:
    {
        "email": "nuevo@ejemplo.com",
        "nombre": "Nuevo Operador",
        "telefono": "+56912345678",
        "id_rol_global": 3,
        "password": "contraseña_temporal"
    }
    
    Response:
    {
        "success": true,
        "operador_id": 5,
        "message": "Operador registrado exitosamente"
    }
    """
    data = request.get_json()
    
    validar_campos_requeridos(data, ['email', 'nombre', 'id_rol_global', 'password'])
    
    # Validar email
    from flask_app.utils.error_handler import validar_email
    validar_email(data['email'])
    
    # Verificar que el rol exista
    rol = RolGlobalModel.buscar_por_id(data['id_rol_global'])
    if not rol:
        raise ValidationError('Rol inválido')
    
    # Crear operador
    operador_id = OperadorModel.crear(data, password=data['password'])
    
    return jsonify({
        'success': True,
        'operador_id': operador_id,
        'message': 'Operador registrado exitosamente'
    }), 201


@auth_bp.route('/cambiar-password', methods=['POST'])
@token_requerido
@manejar_errores
def cambiar_password(operador_actual):
    """
    Endpoint para que un operador cambie su propia contraseña.
    
    POST /api/auth/cambiar-password
    Headers:
        Authorization: Bearer <token>
    Body:
    {
        "password_actual": "contraseña_actual",
        "password_nueva": "nueva_contraseña"
    }
    
    Response:
    {
        "success": true,
        "message": "Contraseña actualizada exitosamente"
    }
    """
    data = request.get_json() or {}

    validar_campos_requeridos(data, ['password_actual', 'password_nueva'])

    password_actual = data.get('password_actual')
    password_nueva = data.get('password_nueva')

    if not password_actual or not password_nueva:
        raise ValidationError('Campos de contraseña incompletos')

    if len(password_nueva) < 8:
        raise ValidationError('La nueva contraseña debe tener al menos 8 caracteres')

    # Obtener email del operador autenticado
    operador_id = operador_actual.get('operador_id')
    operador = OperadorModel.buscar_por_id(operador_id)
    if not operador:
        raise ValidationError('Operador no encontrado')

    email = operador.get('email')
    if not email:
        raise ValidationError('Email del operador no disponible')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener hash actual desde la tabla externa
        cursor.execute(
            "SELECT clave_usuario FROM adrecrear_usuarios WHERE email_usuario = %s",
            (email,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValidationError('Usuario de autenticación no encontrado')

        hashed_raw = row.get('clave_usuario') if isinstance(row, dict) else row[0]
        if not hashed_raw:
            raise ValidationError('No existe contraseña registrada')

        # Verificar contraseña actual
        if not bcrypt.checkpw(password_actual.encode('utf-8'), hashed_raw.encode('utf-8')):
            raise ValidationError('Contraseña actual incorrecta')

        # Generar nuevo hash y actualizar
        nuevo_hash = bcrypt.hashpw(password_nueva.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
        cursor.execute(
            "UPDATE adrecrear_usuarios SET clave_usuario = %s WHERE email_usuario = %s",
            (nuevo_hash, email)
        )
        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Contraseña actualizada exitosamente'
        }), 200

    except ValidationError:
        # Re-lanzar para que el manejador de errores lo capture
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error cambiando contraseña: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@auth_bp.route('/logout', methods=['POST'])
@token_requerido
@manejar_errores
def logout(operador_actual):
    """
    Endpoint para cerrar sesión (invalidar token).
    
    POST /api/auth/logout
    Headers:
        Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "message": "Sesión cerrada exitosamente"
    }
    """
    # TODO: Implementar blacklist de tokens si es necesario
    # Por ahora, el cliente simplemente debe eliminar el token
    
    return jsonify({
        'success': True,
        'message': 'Sesión cerrada exitosamente'
    }), 200
