from flask_app.config.conexion_login import execute_query


class PrioridadModel:
    """
    Modelo para gestionar prioridades de tickets.
    Corresponde a la tabla PRIORIDAD en la base de datos.
    """
    
    @staticmethod
    def listar():
        """
        Lista todas las prioridades disponibles ordenadas por jerarquía.
        
        Returns:
            Lista de prioridades
        """
        query = """
            SELECT id_prioridad, jerarquia, descripcion
            FROM prioridad
            ORDER BY jerarquia ASC
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def buscar_por_id(prioridad_id):
        """
        Busca una prioridad por su ID.
        
        Args:
            prioridad_id: ID de la prioridad
        
        Returns:
            Diccionario con los datos de la prioridad o None
        """
        query = """
            SELECT id_prioridad, jerarquia, descripcion
            FROM prioridad
            WHERE id_prioridad = %s
        """
        return execute_query(query, (prioridad_id,), fetch_one=True)
    
    @staticmethod
    def crear(jerarquia, descripcion):
        """
        Crea una nueva prioridad.
        
        Args:
            jerarquia: Nivel de jerarquía (menor = más prioritario)
            descripcion: Descripción de la prioridad
        
        Returns:
            ID de la prioridad creada
        """
        query = """
            INSERT INTO prioridad (jerarquia, descripcion)
            VALUES (%s, %s)
        """
        return execute_query(query, (jerarquia, descripcion), commit=True)
    
    @staticmethod
    def actualizar(prioridad_id, jerarquia=None, descripcion=None):
        """
        Actualiza una prioridad.
        
        Args:
            prioridad_id: ID de la prioridad
            jerarquia: Nueva jerarquía (opcional)
            descripcion: Nueva descripción (opcional)
        
        Returns:
            True si se actualizó correctamente
        """
        campos = []
        params = []
        
        if jerarquia is not None:
            campos.append("jerarquia = %s")
            params.append(jerarquia)
        
        if descripcion is not None:
            campos.append("descripcion = %s")
            params.append(descripcion)
        
        if not campos:
            return False
        
        params.append(prioridad_id)
        
        query = f"""
            UPDATE prioridad
            SET {', '.join(campos)}
            WHERE id_prioridad = %s
        """
        
        return execute_query(query, tuple(params), commit=True)
