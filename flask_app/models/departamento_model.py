"""
Modelo para gestión de departamentos y miembros
"""
from flask_app.config.conexion_login import execute_query, get_local_db_connection


class DepartamentoModel:
    """Modelo para departamentos del sistema"""
    
    @staticmethod
    def crear_departamento(data):
        """Crea un nuevo departamento"""
        query = """
            INSERT INTO departamento (descripcion, email, operador_default, recibe_externo, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        params = (
            data.get('descripcion'),
            data.get('email'),
            data.get('operador_default'),
            data.get('recibe_externo', 0)
        )
        return execute_query(query, params, insert=True)
    
    @staticmethod
    def buscar_por_id(depto_id):
        """Busca un departamento por ID"""
        query = """
            SELECT id_depto as id, descripcion, email, operador_default, 
                   recibe_externo, created_at
            FROM departamento
            WHERE id_depto = %s AND deleted_at IS NULL
        """
        return execute_query(query, (depto_id,), fetch_one=True)
    
    @staticmethod
    def listar_todos():
        """Lista todos los departamentos"""
        query = """
            SELECT d.id_depto as id, d.descripcion, d.email, d.operador_default,
                   d.recibe_externo, d.created_at,
                   o.nombre as operador_nombre
            FROM departamento d
            LEFT JOIN operador o ON d.operador_default = o.id_operador
            WHERE d.deleted_at IS NULL
            ORDER BY d.descripcion
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def actualizar_departamento(depto_id, data):
        """Actualiza un departamento"""
        query = """
            UPDATE departamento
            SET descripcion = %s, email = %s, operador_default = %s, 
                recibe_externo = %s, updated_at = NOW()
            WHERE id_depto = %s AND deleted_at IS NULL
        """
        params = (
            data.get('descripcion'),
            data.get('email'),
            data.get('operador_default'),
            data.get('recibe_externo'),
            depto_id
        )
        return execute_query(query, params, update=True)


class MiembroDptoModel:
    """Modelo para miembros de departamentos"""
    
    @staticmethod
    def agregar_miembro(id_operador, id_depto, rol='Agente'):
        """Agrega un miembro a un departamento"""
        query = """
            INSERT INTO miembro_dpto (id_operador, id_depto, rol, fecha_asignacion)
            VALUES (%s, %s, %s, NOW())
        """
        return execute_query(query, (id_operador, id_depto, rol), insert=True)
    
    @staticmethod
    def listar_por_departamento(id_depto):
        """Lista miembros de un departamento"""
        query = """
            SELECT m.id_miembro as id, m.id_operador, m.id_depto, m.rol,
                   m.fecha_asignacion, m.fecha_desasignacion,
                   o.nombre as operador_nombre, o.email as operador_email
            FROM miembro_dpto m
            INNER JOIN operador o ON m.id_operador = o.id_operador
            WHERE m.id_depto = %s AND m.fecha_desasignacion IS NULL
            ORDER BY m.rol DESC, o.nombre
        """
        return execute_query(query, (id_depto,), fetch_all=True)
    
    @staticmethod
    def remover_miembro(id_miembro):
        """Remueve un miembro de un departamento"""
        query = """
            UPDATE miembro_dpto
            SET fecha_desasignacion = NOW()
            WHERE id_miembro = %s AND fecha_desasignacion IS NULL
        """
        return execute_query(query, (id_miembro,), update=True)
