from flask_app.config.conexion_login import execute_query


class SLAModel:
    """
    Modelo para gestionar Service Level Agreements (SLA).
    Corresponde a la tabla SLA en la base de datos.
    """
    
    @staticmethod
    def listar(solo_activos=False):
        """
        Lista todos los SLAs disponibles.
        
        Args:
            solo_activos: Si True, solo retorna SLAs activos
        
        Returns:
            Lista de SLAs
        """
        query = """
            SELECT id_sla, nombre, tiempo_primera_respuesta_min, 
                   tiempo_resolucion_min, activo
            FROM sla
        """
        
        if solo_activos:
            query += " WHERE activo = 1"
        
        query += " ORDER BY nombre"
        
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def buscar_por_id(sla_id):
        """
        Busca un SLA por su ID.
        
        Args:
            sla_id: ID del SLA
        
        Returns:
            Diccionario con los datos del SLA o None
        """
        query = """
            SELECT id_sla, nombre, tiempo_primera_respuesta_min, 
                   tiempo_resolucion_min, activo
            FROM sla
            WHERE id_sla = %s
        """
        return execute_query(query, (sla_id,), fetch_one=True)
    
    @staticmethod
    def crear(data):
        """
        Crea un nuevo SLA.
        
        Args:
            data: Diccionario con los datos del SLA
                - nombre: Nombre del SLA
                - tiempo_primera_respuesta_min: Tiempo en minutos
                - tiempo_resolucion_min: Tiempo en minutos
                - activo: 0 o 1
        
        Returns:
            ID del SLA creado
        """
        query = """
            INSERT INTO sla 
            (nombre, tiempo_primera_respuesta_min, tiempo_resolucion_min, activo)
            VALUES (%s, %s, %s, %s)
        """
        
        params = (
            data['nombre'],
            data['tiempo_primera_respuesta_min'],
            data['tiempo_resolucion_min'],
            data.get('activo', 1)
        )
        
        return execute_query(query, params, commit=True)
    
    @staticmethod
    def actualizar(sla_id, data):
        """
        Actualiza un SLA.
        
        Args:
            sla_id: ID del SLA a actualizar
            data: Diccionario con los campos a actualizar
        
        Returns:
            True si se actualizó correctamente
        """
        campos = []
        params = []
        
        campos_permitidos = [
            'nombre', 
            'tiempo_primera_respuesta_min', 
            'tiempo_resolucion_min', 
            'activo'
        ]
        
        for campo in campos_permitidos:
            if campo in data:
                campos.append(f"{campo} = %s")
                params.append(data[campo])
        
        if not campos:
            return False
        
        params.append(sla_id)
        
        query = f"""
            UPDATE sla 
            SET {', '.join(campos)}
            WHERE id_sla = %s
        """
        
        return execute_query(query, tuple(params), commit=True)
    
    @staticmethod
    def activar_desactivar(sla_id, activo):
        """
        Activa o desactiva un SLA.
        
        Args:
            sla_id: ID del SLA
            activo: 1 para activar, 0 para desactivar
        
        Returns:
            True si se actualizó correctamente
        """
        query = """
            UPDATE sla
            SET activo = %s
            WHERE id_sla = %s
        """
        return execute_query(query, (activo, sla_id), commit=True)
