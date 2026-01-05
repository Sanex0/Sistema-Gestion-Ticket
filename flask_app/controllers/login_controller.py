
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_app.config.conexion_login import get_db_connection
import bcrypt

login_bp = Blueprint('login_bp', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Conexión a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT clave_usuario FROM adrecrear_usuarios WHERE email_usuario=%s AND estado_usuario=1", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            hashed = user[0].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), hashed):
                session['usuario'] = username
                return redirect(url_for('login_bp.dashboard'))  # Redirige al dashboard
        flash('Usuario o contraseña incorrectos')
        return render_template('login.html')
    return render_template('login.html')


@login_bp.route('/')
def root():
    return redirect(url_for('login_bp.login'))

@login_bp.route('/dashboard')
def dashboard():
    # Ya no requerimos sesión, el auth lo maneja el frontend con JWT
    return render_template('dashboard.html')

@login_bp.route('/test-login')
def test_login():
    return render_template('test_login.html')
