from flask_app.config.conexion_login import execute_query


class ClubModel:
    """
    Modelo para gestionar clubes/organizaciones.
    Corresponde a la tabla CLUB en la base de datos.
    """
    
    @staticmethod
    def listar():
        """
        Lista todos los clubes disponibles.
        
        Returns:
            Lista de clubes
        """
        query = """
            SELECT id_club, nom_club
            FROM club
            ORDER BY nom_club
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def buscar_por_id(club_id):
        """
        Busca un club por su ID.
        
        Args:
            club_id: ID del club
        
        Returns:
            Diccionario con los datos del club o None
        """
        query = """
            SELECT id_club, nom_club
            FROM club
            WHERE id_club = %s
        """
        return execute_query(query, (club_id,), fetch_one=True)
    
    @staticmethod
    def crear(nom_club):
        """
        Crea un nuevo club.
        
        Args:
            nom_club: Nombre del club
        
        Returns:
            ID del club creado
        """
        query = """
            INSERT INTO club (nom_club)
            VALUES (%s)
        """
        return execute_query(query, (nom_club,), commit=True)
    
    @staticmethod
    def actualizar(club_id, nom_club):
        """
        Actualiza el nombre de un club.
        
        Args:
            club_id: ID del club
            nom_club: Nuevo nombre
        
        Returns:
            True si se actualizó correctamente
        """
        query = """
            UPDATE club
            SET nom_club = %s
            WHERE id_club = %s
        """
        return execute_query(query, (nom_club, club_id), commit=True)
    
    @staticmethod
    def eliminar(club_id):
        """
        Elimina un club.
        
        Args:
            club_id: ID del club a eliminar
        
        Returns:
            True si se eliminó correctamente
        """
        query = """
            DELETE FROM club
            WHERE id_club = %s
        """
        return execute_query(query, (club_id,), commit=True)
