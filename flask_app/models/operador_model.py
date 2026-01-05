"""
Modelo para gestión de operadores y roles globales
"""
from flask_app.config.conexion_login import execute_query, get_local_db_connection


class OperadorModel:
    """Modelo para operadores del sistema"""
    
    @staticmethod
    def buscar_por_email(email):
        """Busca un operador por email"""
        query = """
            SELECT o.id_operador as id, o.email, o.nombre, o.telefono, 
                   o.estado, o.id_rol_global as rol_id,
                   r.nombre as rol_nombre
            FROM operador o
            LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
            WHERE o.email = %s AND o.deleted_at IS NULL
        """
        return execute_query(query, (email,), fetch_one=True)
    
    @staticmethod
    def buscar_por_id(operador_id):
        """Busca un operador por ID"""
        query = """
            SELECT o.id_operador as id, o.email, o.nombre, o.telefono,
                   o.estado, o.id_rol_global as rol_id,
                   r.nombre as rol_nombre
            FROM operador o
            LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
            WHERE o.id_operador = %s AND o.deleted_at IS NULL
        """
        return execute_query(query, (operador_id,), fetch_one=True)
    
    @staticmethod
    def listar_todos():
        """Lista todos los operadores activos"""
        query = """
            SELECT o.id_operador as id, o.email, o.nombre, o.telefono,
                   o.estado, o.id_rol_global as rol_id,
                   r.nombre as rol_nombre
            FROM operador o
            LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
            WHERE o.deleted_at IS NULL
            ORDER BY o.nombre
        """
        return execute_query(query, fetch_all=True)


class RolGlobalModel:
    """Modelo para roles globales"""
    
    @staticmethod
    def listar_activos():
        """Lista todos los roles activos"""
        query = """
            SELECT id_rol as id, nombre, activo
            FROM rol_global
            WHERE activo = 1
            ORDER BY nombre
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def buscar_por_id(rol_id):
        """Busca un rol por ID"""
        query = """
            SELECT id_rol as id, nombre, activo
            FROM rol_global
            WHERE id_rol = %s
        """
        return execute_query(query, (rol_id,), fetch_one=True)
