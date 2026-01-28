import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()


def configurar_logging(app):
    """
    Configura el sistema de logging para la aplicación Flask.
    
    Args:
        app: Instancia de Flask
    """
    # Evitar configurar logging más de una vez
    if getattr(app, "_logging_configured", False):
        return

    # Nivel de logging desde variable de entorno
    log_level_str = os.getenv('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Formato de los logs
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # Handler para archivo (rotativo opcional)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    log_file = os.getenv('LOG_FILE') or os.path.join(project_root, 'app.log')

    # Asegurarse de que el directorio del log exista (evita FileNotFoundError)
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    except Exception:
        # Si no se puede crear el directorio, caemos a log_file relativo 'app.log'
        log_file = 'app.log'

    # En Windows evitar rotación por defecto (WinError 32 por archivo en uso)
    rotate_env = os.getenv('LOG_ROTATE')
    rotate_default = False if os.name == 'nt' else True
    rotate_enabled = rotate_default if rotate_env is None else str(rotate_env).strip().lower() in {'1','true','yes','y','on'}

    if rotate_enabled:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10,
            delay=True
        )
    else:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8', delay=True)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configurar logger raíz (una sola vez)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configurar logger de la aplicación para que propague al root
    app.logger.handlers.clear()
    app.logger.setLevel(log_level)
    app.logger.propagate = True

    app._logging_configured = True
    
    app.logger.info('Sistema de logging configurado')


def log_request(app):
    """
    Registra middleware para loguear todas las peticiones HTTP.
    
    Args:
        app: Instancia de Flask
    """
    
    @app.before_request
    def log_request_info():
        from flask import request
        app.logger.info(f'{request.method} {request.path} - {request.remote_addr}')
    
    @app.after_request
    def log_response_info(response):
        from flask import request
        app.logger.info(
            f'{request.method} {request.path} - Status: {response.status_code}'
        )
        return response
