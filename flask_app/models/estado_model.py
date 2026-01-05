from flask_app.config.conexion_login import execute_query


class EstadoModel:
    """
    Modelo para gestionar estados de tickets.
    Corresponde a la tabla ESTADO en la base de datos.
    """
    
    @staticmethod
    def listar():
        """
        Lista todos los estados disponibles.
        
        Returns:
            Lista de estados
        """
        query = """
            SELECT id_estado, descripcion
            FROM estado
            ORDER BY id_estado
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def buscar_por_id(estado_id):
        """
        Busca un estado por su ID.
        
        Args:
            estado_id: ID del estado
        
        Returns:
            Diccionario con los datos del estado o None
        """
        query = """
            SELECT id_estado, descripcion
            FROM estado
            WHERE id_estado = %s
        """
        return execute_query(query, (estado_id,), fetch_one=True)
    
    @staticmethod
    def crear(descripcion):
        """
        Crea un nuevo estado.
        
        Args:
            descripcion: Descripción del estado
        
        Returns:
            ID del estado creado
        """
        query = """
            INSERT INTO estado (descripcion)
            VALUES (%s)
        """
        return execute_query(query, (descripcion,), commit=True)
    
    @staticmethod
    def actualizar(estado_id, descripcion):
        """
        Actualiza la descripción de un estado.
        
        Args:
            estado_id: ID del estado
            descripcion: Nueva descripción
        
        Returns:
            True si se actualizó correctamente
        """
        query = """
            UPDATE estado
            SET descripcion = %s
            WHERE id_estado = %s
        """
        return execute_query(query, (descripcion, estado_id), commit=True)
