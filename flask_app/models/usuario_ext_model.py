"""
Modelo para gestión de usuarios externos
"""
from flask_app.config.conexion_login import execute_query, get_local_db_connection


class UsuarioExtModel:
    """Modelo para usuarios externos del sistema"""
    
    @staticmethod
    def crear_usuario(data):
        """Crea un nuevo usuario externo"""
        query = """
            INSERT INTO usuario_ext (rut, nombre, telefono, email, existe_flex)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            data.get('rut'),
            data.get('nombre'),
            data.get('telefono'),
            data.get('email'),
            data.get('existe_flex', 0)
        )
        return execute_query(query, params, commit=True)
    
    @staticmethod
    def buscar_por_email(email):
        """Busca un usuario por email"""
        query = """
            SELECT id_usuario as id, rut, nombre, telefono, email
            FROM usuario_ext
            WHERE email = %s AND deleted_at IS NULL
        """
        return execute_query(query, (email,), fetch_one=True)
    
    @staticmethod
    def buscar_por_id(usuario_id):
        """Busca un usuario por ID"""
        query = """
            SELECT id_usuario as id, rut, nombre, telefono, email
            FROM usuario_ext
            WHERE id_usuario = %s AND deleted_at IS NULL
        """
        return execute_query(query, (usuario_id,), fetch_one=True)
    
    @staticmethod
    def buscar_por_rut(rut):
        """Busca un usuario por RUT"""
        query = """
            SELECT id_usuario as id, rut, nombre, telefono, email
            FROM usuario_ext
            WHERE rut = %s AND deleted_at IS NULL
        """
        return execute_query(query, (rut,), fetch_one=True)
    
    @staticmethod
    def actualizar_usuario(usuario_id, data):
        """Actualiza un usuario existente"""
        query = """
            UPDATE usuario_ext
            SET nombre = %s, telefono = %s, email = %s, updated_at = NOW()
            WHERE id_usuario = %s AND deleted_at IS NULL
        """
        params = (
            data.get('nombre'),
            data.get('telefono'),
            data.get('email'),
            usuario_id
        )
        return execute_query(query, params, update=True)
    
    @staticmethod
    def listar_todos():
        """Lista todos los usuarios externos"""
        query = """
            SELECT id_usuario as id, rut, nombre, telefono, email
            FROM usuario_ext
            WHERE deleted_at IS NULL
            ORDER BY nombre
        """
        return execute_query(query, fetch_all=True)
