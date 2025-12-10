from flask import Flask

from flask_app.controllers.login_controller import login_bp

app = Flask(__name__)
app.secret_key = 'clave_muy_secreta'  # Necesario para usar flash messages

app.register_blueprint(login_bp)

if __name__ == "__main__":
    app.run(debug=True)
