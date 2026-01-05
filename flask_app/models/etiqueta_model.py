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
            INSERT INTO etiqueta (nombre, color, descripcion, created_at)
            VALUES (%s, %s, %s, NOW())
        """
        params = (
            data.get('nombre'),
            color,
            data.get('descripcion')
        )
        return execute_query(query, params, insert=True)
    
    @staticmethod
    def buscar_por_id(etiqueta_id):
        """Busca una etiqueta por ID"""
        query = """
            SELECT id_etiqueta as id, nombre, color, descripcion, created_at
            FROM etiqueta
            WHERE id_etiqueta = %s AND deleted_at IS NULL
        """
        return execute_query(query, (etiqueta_id,), fetch_one=True)
    
    @staticmethod
    def listar_todas():
        """Lista todas las etiquetas"""
        query = """
            SELECT id_etiqueta as id, nombre, color, descripcion, created_at
            FROM etiqueta
            WHERE deleted_at IS NULL
            ORDER BY nombre
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def asignar_a_ticket(id_etiqueta, id_ticket):
        """Asigna una etiqueta a un ticket"""
        query = """
            INSERT INTO ticket_etiqueta (id_ticket, id_etiqueta, fecha_asignacion)
            VALUES (%s, %s, NOW())
        """
        return execute_query(query, (id_ticket, id_etiqueta), insert=True)
    
    @staticmethod
    def desasignar_de_ticket(id_etiqueta, id_ticket):
        """Desasigna una etiqueta de un ticket"""
        query = """
            DELETE FROM ticket_etiqueta
            WHERE id_ticket = %s AND id_etiqueta = %s
        """
        return execute_query(query, (id_ticket, id_etiqueta), update=True)
    
    @staticmethod
    def listar_por_ticket(id_ticket):
        """Lista etiquetas de un ticket"""
        query = """
            SELECT e.id_etiqueta as id, e.nombre, e.color, e.descripcion,
                   te.fecha_asignacion
            FROM etiqueta e
            INNER JOIN ticket_etiqueta te ON e.id_etiqueta = te.id_etiqueta
            WHERE te.id_ticket = %s AND e.deleted_at IS NULL
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
            SET nombre = %s, color = %s, descripcion = %s, updated_at = NOW()
            WHERE id_etiqueta = %s AND deleted_at IS NULL
        """
        params = (
            data.get('nombre'),
            data.get('color'),
            data.get('descripcion'),
            etiqueta_id
        )
        return execute_query(query, params, update=True)
