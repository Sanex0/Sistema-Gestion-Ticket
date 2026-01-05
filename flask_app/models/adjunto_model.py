from flask_app.config.conexion_login import execute_query, get_local_db_connection
from datetime import datetime
import os


class AdjuntoModel:
    """
    Modelo para gestionar archivos adjuntos de mensajes.
    Los adjuntos están siempre asociados a un mensaje.
    """
    
    @staticmethod
    def crear_adjunto(data):
        """
        Registra un nuevo adjunto en la base de datos.
        
        Args:
            data: dict con {
                'nom_adj': str - Nombre del archivo,
                'ruta': str - Ruta donde se guardó el archivo,
                'id_msg': int - ID del mensaje al que pertenece
            }
        
        Returns:
            dict: {'id_adj': int}
        """
        query = """
            INSERT INTO adjunto (nom_adj, ruta, id_msg)
            VALUES (%s, %s, %s)
        """
        
        params = (
            data['nom_adj'],
            data['ruta'],
            data['id_msg']
        )
        
        id_adj = execute_query(query, params, commit=True)
        return {'id_adj': id_adj}
    
    @staticmethod
    def buscar_por_id(id_adj):
        """
        Busca un adjunto por su ID.
        
        Args:
            id_adj: int
        
        Returns:
            dict o None
        """
        query = """
            SELECT a.*, m.id_ticket
            FROM adjunto a
            INNER JOIN mensaje m ON a.id_msg = m.id_msg
            WHERE a.id_adj = %s AND a.deleted_at IS NULL
        """
        
        return execute_query(query, (id_adj,), fetch_one=True)
    
    @staticmethod
    def listar_por_mensaje(id_msg):
        """
        Lista todos los adjuntos de un mensaje.
        
        Args:
            id_msg: int
        
        Returns:
            list de dict
        """
        query = """
            SELECT * FROM adjunto
            WHERE id_msg = %s AND deleted_at IS NULL
            ORDER BY id_adj ASC
        """
        
        return execute_query(query, (id_msg,), fetch_all=True)
    
    @staticmethod
    def listar_por_ticket(id_ticket):
        """
        Lista todos los adjuntos de un ticket (de todos sus mensajes).
        
        Args:
            id_ticket: int
        
        Returns:
            list de dict
        """
        query = """
            SELECT 
                a.*,
                m.asunto as mensaje_asunto,
                m.fecha_envio as mensaje_fecha,
                m.remitente_tipo,
                CASE 
                    WHEN m.remitente_tipo = 'Usuario' THEN u.nombre
                    WHEN m.remitente_tipo = 'Operador' THEN o.nombre
                END as remitente_nombre
            FROM adjunto a
            INNER JOIN mensaje m ON a.id_msg = m.id_msg
            LEFT JOIN usuario_ext u ON m.remitente_tipo = 'Usuario' AND m.remitente_id = u.id_usuario
            LEFT JOIN operador o ON m.remitente_tipo = 'Operador' AND m.remitente_id = o.id_operador
            WHERE m.id_ticket = %s AND a.deleted_at IS NULL
            ORDER BY m.fecha_envio DESC, a.id_adj ASC
        """
        
        return execute_query(query, (id_ticket,), fetch_all=True)
    
    @staticmethod
    def eliminar_adjunto(id_adj, deleted_by=None, soft_delete=True):
        """
        Elimina un adjunto.
        
        Args:
            id_adj: int
            deleted_by: int - ID del operador que elimina
            soft_delete: bool - Si True, marca como eliminado. Si False, elimina físicamente.
        
        Returns:
            bool: True si se eliminó, False si no existe
        """
        # Primero obtener la ruta del archivo
        adjunto = AdjuntoModel.buscar_por_id(id_adj)
        
        if not adjunto:
            return False
        
        if soft_delete:
            query = """
                UPDATE adjunto 
                SET deleted_at = %s,
                    deleted_by = %s
                WHERE id_adj = %s
            """
            params = (datetime.now(), deleted_by, id_adj)
            execute_query(query, params, commit=True)
        else:
            query = "DELETE FROM adjunto WHERE id_adj = %s"
            execute_query(query, (id_adj,), commit=True)
            
            # Eliminar archivo físico si existe
            if adjunto.get('ruta') and os.path.exists(adjunto['ruta']):
                try:
                    os.remove(adjunto['ruta'])
                except Exception as e:
                    print(f"Error al eliminar archivo físico: {e}")
        
        return True
    
    @staticmethod
    def obtener_estadisticas_ticket(id_ticket):
        """
        Obtiene estadísticas de adjuntos de un ticket.
        
        Args:
            id_ticket: int
        
        Returns:
            dict con estadísticas
        """
        query = """
            SELECT 
                COUNT(a.id_adj) as total_adjuntos,
                COUNT(DISTINCT a.id_msg) as mensajes_con_adjuntos,
                SUM(CASE WHEN a.deleted_at IS NULL THEN 1 ELSE 0 END) as adjuntos_activos,
                SUM(CASE WHEN a.deleted_at IS NOT NULL THEN 1 ELSE 0 END) as adjuntos_eliminados
            FROM adjunto a
            INNER JOIN mensaje m ON a.id_msg = m.id_msg
            WHERE m.id_ticket = %s
        """
        
        return execute_query(query, (id_ticket,), fetch_one=True)
    
    @staticmethod
    def validar_archivo(filename, max_size_mb=10):
        """
        Valida un archivo antes de subirlo.
        
        Args:
            filename: str - Nombre del archivo
            max_size_mb: int - Tamaño máximo en MB
        
        Returns:
            tuple: (bool, str) - (es_valido, mensaje_error)
        """
        # Extensiones permitidas
        ALLOWED_EXTENSIONS = {
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
            'txt', 'csv',
            'jpg', 'jpeg', 'png', 'gif', 'bmp',
            'zip', 'rar', '7z',
            'mp3', 'mp4', 'avi', 'mov'
        }
        
        if not filename:
            return False, "Nombre de archivo vacío"
        
        # Verificar extensión
        if '.' not in filename:
            return False, "Archivo sin extensión"
        
        ext = filename.rsplit('.', 1)[1].lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Extensión .{ext} no permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        
        return True, "OK"
    
    @staticmethod
    def generar_nombre_unico(filename):
        """
        Genera un nombre único para el archivo.
        
        Args:
            filename: str - Nombre original del archivo
        
        Returns:
            str: Nombre único
        """
        import uuid
        
        # Separar nombre y extensión
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            # Generar nombre único: timestamp_uuid.ext
            unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        else:
            unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        return unique_name
    
    @staticmethod
    def obtener_ruta_almacenamiento():
        """
        Obtiene la ruta base para almacenar archivos.
        
        Returns:
            str: Ruta absoluta del directorio de uploads
        """
        # Ruta base del proyecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Directorio de uploads
        upload_dir = os.path.join(base_dir, 'uploads')
        
        # Crear directorio si no existe
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        return upload_dir
    
    @staticmethod
    def obtener_ruta_por_ticket(id_ticket):
        """
        Obtiene la ruta para archivos de un ticket específico.
        
        Args:
            id_ticket: int
        
        Returns:
            str: Ruta del directorio para el ticket
        """
        upload_dir = AdjuntoModel.obtener_ruta_almacenamiento()
        ticket_dir = os.path.join(upload_dir, f"ticket_{id_ticket}")
        
        # Crear directorio si no existe
        if not os.path.exists(ticket_dir):
            os.makedirs(ticket_dir)
        
        return ticket_dir
