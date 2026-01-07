"""
Modelo para gestión de etiquetas
"""
import re
from flask_app.config.conexion_login import execute_query, get_local_db_connection


class EtiquetaModel:
    """Modelo para etiquetas de tickets"""
    
    @staticmethod
    def validar_color(color):
        """Valida que el color sea un código hexadecimal válido"""
        patron = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        return bool(re.match(patron, color))
    
    @staticmethod
    def crear_etiqueta(data):
        """Crea una nueva etiqueta"""
        color = data.get('color', '#000000')
        if not EtiquetaModel.validar_color(color):
            raise ValueError('Color debe ser un código hexadecimal válido')
        
        query = """
            INSERT INTO etiqueta (nombre, color)
            VALUES (%s, %s)
        """
        params = (
            data.get('nombre'),
            color,
        )
        id_etiqueta = execute_query(query, params, commit=True)
        return {'id_etiqueta': id_etiqueta}

    @staticmethod
    def buscar_por_nombre(nombre):
        """Busca una etiqueta por nombre exacto (no eliminada)"""
        query = """
            SELECT id_etiqueta as id, nombre, color
            FROM etiqueta
            WHERE nombre = %s
        """
        return execute_query(query, (nombre,), fetch_one=True)
    
    @staticmethod
    def buscar_por_id(etiqueta_id):
        """Busca una etiqueta por ID"""
        query = """
            SELECT id_etiqueta as id, nombre, color
            FROM etiqueta
            WHERE id_etiqueta = %s
        """
        return execute_query(query, (etiqueta_id,), fetch_one=True)
    
    @staticmethod
    def listar_todas():
        """Lista todas las etiquetas"""
        query = """
            SELECT id_etiqueta as id, nombre, color
            FROM etiqueta
            ORDER BY nombre
        """
        return execute_query(query, fetch_all=True)

    @staticmethod
    def listar():
        """Alias para mantener compatibilidad con el controller."""
        return EtiquetaModel.listar_todas()
    
    @staticmethod
    def asignar_a_ticket(id_ticket, id_etiqueta):
        """Asigna una etiqueta a un ticket"""
        query = """
            INSERT IGNORE INTO ticket_etiqueta (id_ticket, id_etiqueta)
            VALUES (%s, %s)
        """
        execute_query(query, (id_ticket, id_etiqueta), commit=True)
        return True
    
    @staticmethod
    def desasignar_de_ticket(id_ticket, id_etiqueta):
        """Desasigna una etiqueta de un ticket"""
        query = """
            DELETE FROM ticket_etiqueta
            WHERE id_ticket = %s AND id_etiqueta = %s
        """
        execute_query(query, (id_ticket, id_etiqueta), commit=True)
        return True
    
    @staticmethod
    def listar_por_ticket(id_ticket):
        """Lista etiquetas de un ticket"""
        query = """
            SELECT e.id_etiqueta as id, e.nombre, e.color
            FROM etiqueta e
            INNER JOIN ticket_etiqueta te ON e.id_etiqueta = te.id_etiqueta
            WHERE te.id_ticket = %s
            ORDER BY e.nombre
        """
        return execute_query(query, (id_ticket,), fetch_all=True)
    
    @staticmethod
    def actualizar_etiqueta(etiqueta_id, data):
        """Actualiza una etiqueta"""
        if 'color' in data and not EtiquetaModel.validar_color(data['color']):
            raise ValueError('Color debe ser un código hexadecimal válido')
        
        query = """
            UPDATE etiqueta
            SET nombre = %s, color = %s
            WHERE id_etiqueta = %s
        """
        params = (
            data.get('nombre'),
            data.get('color'),
            etiqueta_id
        )
        execute_query(query, params, commit=True)
        return True

    @staticmethod
    def eliminar_etiqueta(etiqueta_id, soft_delete=True):
        """Elimina una etiqueta (soft-delete por defecto) y sus asociaciones."""
        # El esquema actual no tiene deleted_at, así que eliminamos físicamente.
        execute_query(
            "DELETE FROM ticket_etiqueta WHERE id_etiqueta = %s",
            (etiqueta_id,),
            commit=True,
        )
        execute_query(
            "DELETE FROM etiqueta WHERE id_etiqueta = %s",
            (etiqueta_id,),
            commit=True,
        )
        return True

    @staticmethod
    def listar_tickets_por_etiqueta(etiqueta_id):
        """Lista tickets asociados a una etiqueta."""
        query = """
            SELECT
                t.id_ticket,
                t.asunto,
                t.id_estado,
                t.id_prioridad,
                t.fecha_creacion,
                t.id_operador,
                t.id_usuarioext
            FROM ticket t
            INNER JOIN ticket_etiqueta te ON te.id_ticket = t.id_ticket
            WHERE te.id_etiqueta = %s
            ORDER BY t.fecha_creacion DESC
        """
        return execute_query(query, (etiqueta_id,), fetch_all=True)

    @staticmethod
    def reemplazar_etiquetas_ticket(id_ticket, etiquetas):
        """Reemplaza todas las etiquetas de un ticket por una lista de IDs."""
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM ticket_etiqueta WHERE id_ticket = %s", (id_ticket,))

            for id_etiqueta in etiquetas:
                cursor.execute(
                    "INSERT IGNORE INTO ticket_etiqueta (id_ticket, id_etiqueta) VALUES (%s, %s)",
                    (id_ticket, id_etiqueta),
                )

            conn.commit()
            return True
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
