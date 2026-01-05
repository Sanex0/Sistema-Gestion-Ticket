from flask import jsonify
from functools import wraps
import logging


class AppError(Exception):
    """Clase base para errores de la aplicación."""
    
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['success'] = False
        rv['error'] = self.message
        return rv


class ValidationError(AppError):
    """Error de validación de datos."""
    
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=400, payload=payload)


class AuthenticationError(AppError):
    """Error de autenticación."""
    
    def __init__(self, message='Credenciales inválidas', payload=None):
        super().__init__(message, status_code=401, payload=payload)


class AuthorizationError(AppError):
    """Error de autorización/permisos."""
    
    def __init__(self, message='No tiene permisos para realizar esta acción', payload=None):
        super().__init__(message, status_code=403, payload=payload)


class NotFoundError(AppError):
    """Recurso no encontrado."""
    
    def __init__(self, message='Recurso no encontrado', payload=None):
        super().__init__(message, status_code=404, payload=payload)


class DatabaseError(AppError):
    """Error de base de datos."""
    
    def __init__(self, message='Error en la base de datos', payload=None):
        super().__init__(message, status_code=500, payload=payload)


def manejar_errores(f):
    """
    Decorador para manejar errores de forma centralizada en los endpoints.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppError as e:
            logging.error(f"AppError en {f.__name__}: {e.message}")
            return jsonify(e.to_dict()), e.status_code
        except ValueError as e:
            logging.error(f"ValueError en {f.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logging.exception(f"Error inesperado en {f.__name__}")
            return jsonify({
                'success': False,
                'error': 'Error interno del servidor',
                'details': str(e) if logging.getLogger().level == logging.DEBUG else None
            }), 500
    
    return wrapper


def validar_campos_requeridos(data, campos_requeridos):
    """
    Valida que todos los campos requeridos estén presentes en el diccionario.
    
    Args:
        data: Diccionario con los datos
        campos_requeridos: Lista de nombres de campos requeridos
    
    Raises:
        ValidationError: Si falta algún campo requerido
    """
    campos_faltantes = [campo for campo in campos_requeridos if campo not in data or data[campo] is None]
    
    if campos_faltantes:
        raise ValidationError(
            f"Campos requeridos faltantes: {', '.join(campos_faltantes)}"
        )


def validar_email(email):
    """
    Valida que el email tenga un formato válido.
    
    Args:
        email: Email a validar
    
    Returns:
        bool: True si el email es válido
    
    Raises:
        ValidationError: Si el email no es válido
    """
    import re
    
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(patron, email):
        raise ValidationError(f"Email inválido: {email}")
    
    return True


def registrar_error(app):
    """
    Registra los manejadores de errores globales en la aplicación Flask.
    
    Args:
        app: Instancia de Flask
    """
    
    @app.errorhandler(AppError)
    def handle_app_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint no encontrado'
        }), 404
    
    @app.errorhandler(405)
    def handle_405(error):
        return jsonify({
            'success': False,
            'error': 'Método HTTP no permitido'
        }), 405
    
    @app.errorhandler(500)
    def handle_500(error):
        logging.exception('Error 500')
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        }), 500
