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
    # Nivel de logging desde variable de entorno
    log_level_str = os.getenv('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Formato de los logs
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # Handler para archivo (rotativo)
    log_file = os.getenv('LOG_FILE', 'app.log')

    # Asegurarse de que el directorio del log exista (evita FileNotFoundError)
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    except Exception:
        # Si no se puede crear el directorio, caemos a log_file relativo 'app.log'
        log_file = 'app.log'

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configurar logger de la aplicación
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
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
