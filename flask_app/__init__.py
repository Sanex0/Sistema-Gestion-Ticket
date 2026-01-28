from flask import Flask, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
from datetime import timedelta

# Cargar variables de entorno
load_dotenv()

# Importar blueprints
from flask_app.controllers.login_controller import login_bp
from flask_app.controllers.ticket_controller import ticket_bp
from flask_app.controllers.auth_controller import auth_bp
from flask_app.controllers.mensaje_controller import mensaje_bp
from flask_app.controllers.adjunto_controller import adjunto_bp
from flask_app.controllers.departamento_controller import departamento_bp
from flask_app.controllers.etiqueta_controller import etiqueta_bp
from flask_app.controllers.notificacion_controller import notificacion_bp
from flask_app.controllers.catalogo_controller import catalogo_bp
from flask_app.controllers.operador_controller import operador_bp
from flask_app.controllers.admin_controller import admin_bp
from flask_app.controllers.inbound_controller import inbound_bp

# Importar utilidades
from flask_app.utils.error_handler import registrar_error
from flask_app.utils.logger import configurar_logging, log_request

app = Flask(__name__)

# Configuración
app.secret_key = os.getenv('SECRET_KEY', 'clave_muy_secreta_cambiar_en_produccion')
app.config['JSON_AS_ASCII'] = False  # Para soportar caracteres especiales
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB
# Session configuration: duración por defecto y renovación en cada petición
app.permanent_session_lifetime = timedelta(days=int(os.getenv('SESSION_LIFETIME_DAYS', 7)))
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# Configurar CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configurar logging
configurar_logging(app)
log_request(app)

# Registrar manejadores de errores
registrar_error(app)

# Registrar blueprints
app.register_blueprint(login_bp)
app.register_blueprint(ticket_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(mensaje_bp)
app.register_blueprint(adjunto_bp)
app.register_blueprint(departamento_bp)
app.register_blueprint(etiqueta_bp)
app.register_blueprint(notificacion_bp)
app.register_blueprint(catalogo_bp)
app.register_blueprint(operador_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(inbound_bp)

# Health check global
@app.route('/health', methods=['GET'])
def health():
    return {
        'status': 'ok',
        'service': 'Sistema de Gestión de Tickets',
        'version': '2.0.0'
    }, 200


# Renovar sesión (rolling) cuando el usuario está activo
@app.before_request
def refresh_session():
    try:
        if session.get('usuario'):
            session.modified = True
    except Exception:
        pass

if __name__ == "__main__":
    app.run(debug=True)
