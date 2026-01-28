import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt_secret_key_cambiar_en_produccion')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 28800))  # 8 horas (por defecto)
JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 días


def generar_token(operador_id, email, rol, tipo='access'):
    """
    Genera un token JWT para un operador.
    
    Args:
        operador_id: ID del operador
        email: Email del operador
        rol: Rol del operador
        tipo: 'access' o 'refresh'
    
    Returns:
        Token JWT como string
    """
    expiracion = JWT_ACCESS_TOKEN_EXPIRES if tipo == 'access' else JWT_REFRESH_TOKEN_EXPIRES
    
    payload = {
        'operador_id': operador_id,
        'email': email,
        'rol': rol,
        'tipo': tipo,
        'exp': datetime.utcnow() + timedelta(seconds=expiracion),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verificar_token(token):
    """
    Verifica y decodifica un token JWT.
    
    Args:
        token: Token JWT a verificar
    
    Returns:
        Diccionario con el payload del token o None si es inválido
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expirado'}
    except jwt.InvalidTokenError:
        return {'error': 'Token inválido'}


def token_requerido(f):
    """
    Decorador para proteger endpoints que requieren autenticación.
    Extrae el token del header Authorization y lo valida.
    """
    @wraps(f)
    def decorador(*args, **kwargs):
        token = None
        
        # Buscar token en el header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Formato: "Bearer <token>"
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de token inválido. Use: Bearer <token>'
                }), 401
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token de autenticación no proporcionado'
            }), 401
        
        # Verificar token
        payload = verificar_token(token)
        
        if payload is None or 'error' in payload:
            return jsonify({
                'success': False,
                'error': payload.get('error', 'Token inválido')
            }), 401
        
        # Verificar que sea un token de acceso
        if payload.get('tipo') != 'access':
            return jsonify({
                'success': False,
                'error': 'Token inválido. Se requiere un token de acceso'
            }), 401
        
        # Pasar la información del operador a la función
        return f(operador_actual=payload, *args, **kwargs)
    
    return decorador


def rol_requerido(*roles_permitidos):
    """
    Decorador para proteger endpoints que requieren un rol específico.
    Debe usarse después de @token_requerido
    
    Ejemplo:
        @token_requerido
        @rol_requerido('Admin', 'Supervisor')
        def mi_endpoint(operador_actual):
            ...
    """
    def decorador(f):
        @wraps(f)
        def wrapper(operador_actual, *args, **kwargs):
            rol_actual = operador_actual.get('rol')
            
            if rol_actual not in roles_permitidos:
                return jsonify({
                    'success': False,
                    'error': f'Permiso denegado. Se requiere uno de los siguientes roles: {", ".join(roles_permitidos)}'
                }), 403
            
            return f(operador_actual=operador_actual, *args, **kwargs)
        
        return wrapper
    return decorador


def extraer_token_opcional():
    """
    Extrae el token JWT del request si existe, pero no falla si no está presente.
    Útil para endpoints que pueden funcionar con o sin autenticación.
    
    Returns:
        Diccionario con el payload del token o None
    """
    token = None
    
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return None
    
    if not token:
        return None
    
    payload = verificar_token(token)
    
    if payload is None or 'error' in payload:
        return None
    
    return payload
