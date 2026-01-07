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
            INSERT INTO departamento (descripcion, email, operador_default, recibe_externo)
            VALUES (%s, %s, %s, %s)
        """
        params = (
            data.get('descripcion'),
            data.get('email'),
            data.get('operador_default'),
            data.get('recibe_externo', 0)
        )
        id_depto = execute_query(query, params, commit=True)
        return {'id_depto': id_depto}
    
    @staticmethod
    def buscar_por_id(depto_id):
        """Busca un departamento por ID"""
        query = """
            SELECT id_depto as id, descripcion, email, operador_default, recibe_externo
            FROM departamento
            WHERE id_depto = %s
        """
        return execute_query(query, (depto_id,), fetch_one=True)
    
    @staticmethod
    def listar_todos():
        """Lista todos los departamentos"""
        query = """
            SELECT d.id_depto as id, d.descripcion, d.email, d.operador_default,
                   d.recibe_externo,
                   o.nombre as operador_nombre
            FROM departamento d
            LEFT JOIN operador o ON d.operador_default = o.id_operador
            ORDER BY d.descripcion
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def listar(incluir_no_externos=True):
        """Lista departamentos con opción de filtrar por externos"""
        if incluir_no_externos:
            query = """
                SELECT d.id_depto as id_departamento, d.descripcion as nombre, 
                       d.email, d.recibe_externo
                FROM departamento d
                ORDER BY d.descripcion
            """
        else:
            query = """
                SELECT d.id_depto as id_departamento, d.descripcion as nombre,
                       d.email, d.recibe_externo
                FROM departamento d
                WHERE d.recibe_externo = 1
                ORDER BY d.descripcion
            """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def actualizar_departamento(depto_id, data):
        """Actualiza un departamento"""
        query = """
            UPDATE departamento
            SET descripcion = %s, email = %s, operador_default = %s, 
                recibe_externo = %s
            WHERE id_depto = %s
        """
        params = (
            data.get('descripcion'),
            data.get('email'),
            data.get('operador_default'),
            data.get('recibe_externo'),
            depto_id
        )
        execute_query(query, params, commit=True)
        return True

    @staticmethod
    def eliminar_departamento(depto_id):
        """Elimina un departamento solo si no tiene miembros activos."""
        activos = execute_query(
            """
            SELECT COUNT(*) as total
            FROM miembro_dpto
            WHERE id_depto = %s AND fecha_desasignacion IS NULL
            """,
            (depto_id,),
            fetch_one=True,
        )
        total_activos = (activos or {}).get('total', 0)
        if total_activos and int(total_activos) > 0:
            return False, 'No se puede eliminar: tiene miembros activos'

        # Limpieza de miembros históricos y del propio departamento
        execute_query("DELETE FROM miembro_dpto WHERE id_depto = %s", (depto_id,), commit=True)
        execute_query("DELETE FROM departamento WHERE id_depto = %s", (depto_id,), commit=True)
        return True, 'Departamento eliminado exitosamente'


class MiembroDptoModel:
    """Modelo para miembros de departamentos"""
    
    @staticmethod
    def listar_por_departamento(id_depto, solo_activos=True):
        """Lista miembros de un departamento."""
        where_activos = "AND m.fecha_desasignacion IS NULL" if solo_activos else ""
        query = f"""
            SELECT
                m.id_operador,
                m.id_depto,
                m.rol,
                m.fecha_asignacion,
                m.fecha_desasignacion,
                o.nombre as operador_nombre,
                o.email as operador_email
            FROM miembro_dpto m
            INNER JOIN operador o ON m.id_operador = o.id_operador
            WHERE m.id_depto = %s {where_activos}
            ORDER BY FIELD(m.rol, 'Jefe','Supervisor','Agente'), o.nombre
        """
        return execute_query(query, (id_depto,), fetch_all=True)

    @staticmethod
    def asignar_miembro(data):
        """Asigna (o reactiva) un operador en un departamento."""
        query = """
            INSERT INTO miembro_dpto (id_operador, id_depto, rol, fecha_asignacion, fecha_desasignacion)
            VALUES (%s, %s, %s, NOW(), NULL)
            ON DUPLICATE KEY UPDATE
                rol = VALUES(rol),
                fecha_asignacion = NOW(),
                fecha_desasignacion = NULL
        """
        params = (data.get('id_operador'), data.get('id_depto'), data.get('rol'))
        execute_query(query, params, commit=True)
        return True

    @staticmethod
    def desasignar_miembro(id_operador, id_depto):
        """Desasigna (marca fecha_desasignacion) un operador del depto."""
        query = """
            UPDATE miembro_dpto
            SET fecha_desasignacion = NOW()
            WHERE id_operador = %s AND id_depto = %s AND fecha_desasignacion IS NULL
        """
        execute_query(query, (id_operador, id_depto), commit=True)
        return True

    @staticmethod
    def cambiar_rol_miembro(id_operador, id_depto, rol):
        """Cambia el rol de un miembro activo del departamento."""
        query = """
            UPDATE miembro_dpto
            SET rol = %s
            WHERE id_operador = %s AND id_depto = %s AND fecha_desasignacion IS NULL
        """
        execute_query(query, (rol, id_operador, id_depto), commit=True)
        return True

