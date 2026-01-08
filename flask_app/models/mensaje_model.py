from flask_app.config.conexion_login import execute_query, get_local_db_connection
from datetime import datetime


class MensajeModel:
    """
    Modelo para gestionar mensajes de tickets.
    Flujo principal: Email → Sistema → Chat
    """
    
    @staticmethod
    def crear_mensaje(data):
        """
        Crea un nuevo mensaje en un ticket.
        
        Args:
            data: dict con {
                'tipo_mensaje': 'Privado' o 'Publico',
                'asunto': str (max 50),
                'contenido': str (max 500),
                'remitente_id': int,
                'remitente_tipo': 'Usuario' o 'Operador',
                'id_ticket': int,
                'id_canal': int (1=Email, 2=Web, 3=Teléfono, 4=WhatsApp, 5=Chat)
            }
        
        Returns:
            dict: {'id_msg': int}
        """
        from flask_app.config.conexion_login import get_local_db_connection
        import pymysql.cursors
        
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Insertar mensaje
            query = """
                INSERT INTO mensaje 
                (tipo_mensaje, asunto, contenido, remitente_id, remitente_tipo, 
                 estado_mensaje, id_ticket, id_canal)
                VALUES (%s, %s, %s, %s, %s, 'Normal', %s, %s)
            """
            
            params = (
                data.get('tipo_mensaje', 'Publico'),
                data['asunto'],
                data.get('contenido'),
                data['remitente_id'],
                data['remitente_tipo'],
                data['id_ticket'],
                data.get('id_canal', 1)  # Default: Email
            )
            
            cursor.execute(query, params)
            id_msg = cursor.lastrowid
            
            # Registrar en historial
            remitente_tipo = data['remitente_tipo']
            tipo_mensaje = data.get('tipo_mensaje', 'Publico')
            
            if remitente_tipo == 'Operador':
                # Operador envió mensaje
                cursor.execute("""
                    INSERT INTO historial_acciones_ticket 
                    (id_ticket, id_operador, accion, valor_nuevo)
                    VALUES (%s, %s, %s, %s)
                """, (data['id_ticket'], data['remitente_id'], 
                      f'Mensaje {tipo_mensaje.lower()}', data['asunto']))
            else:
                # Usuario envió mensaje
                cursor.execute("""
                    INSERT INTO historial_acciones_ticket 
                    (id_ticket, id_usuarioext, accion, valor_nuevo)
                    VALUES (%s, %s, %s, %s)
                """, (data['id_ticket'], data['remitente_id'], 
                      f'Mensaje {tipo_mensaje.lower()}', data['asunto']))
            
            conn.commit()
            return {'id_msg': id_msg}
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def _truncate_historial_value(value, max_len=100):
        if value is None:
            return None
        return str(value)[:max_len]
    
    @staticmethod
    def buscar_por_id(id_msg):
        """
        Busca un mensaje por su ID.
        
        Args:
            id_msg: int
        
        Returns:
            dict o None
        """
        query = """
            SELECT 
                m.*,
                c.nombre as canal_nombre,
                CASE 
                    WHEN m.remitente_tipo = 'Usuario' THEN u.nombre
                    WHEN m.remitente_tipo = 'Operador' THEN o.nombre
                END as remitente_nombre,
                CASE 
                    WHEN m.remitente_tipo = 'Usuario' THEN u.email
                    WHEN m.remitente_tipo = 'Operador' THEN o.email
                END as remitente_email
            FROM mensaje m
            LEFT JOIN canal c ON m.id_canal = c.id_canal
            LEFT JOIN usuario_ext u ON m.remitente_tipo = 'Usuario' AND m.remitente_id = u.id_usuario
            LEFT JOIN operador o ON m.remitente_tipo = 'Operador' AND m.remitente_id = o.id_operador
            WHERE m.id_msg = %s AND m.deleted_at IS NULL
        """
        
        return execute_query(query, (id_msg,), fetch_one=True)
    
    @staticmethod
    def listar_por_ticket(id_ticket, incluir_privados=False, tipo_usuario=None):
        """
        Lista todos los mensajes de un ticket.
        
        Args:
            id_ticket: int
            incluir_privados: bool - Si True, incluye mensajes privados (solo operadores)
            tipo_usuario: str - 'Usuario' o 'Operador' (para filtrar visibilidad)
        
        Returns:
            list de dict
        """
        query = """
            SELECT 
                m.*,
                c.nombre as canal_nombre,
                CASE 
                    WHEN m.remitente_tipo = 'Usuario' THEN u.nombre
                    WHEN m.remitente_tipo = 'Operador' THEN o.nombre
                END as remitente_nombre,
                CASE 
                    WHEN m.remitente_tipo = 'Usuario' THEN u.email
                    WHEN m.remitente_tipo = 'Operador' THEN o.email
                END as remitente_email,
                (SELECT COUNT(*) FROM adjunto a WHERE a.id_msg = m.id_msg) as total_adjuntos
            FROM mensaje m
            LEFT JOIN canal c ON m.id_canal = c.id_canal
            LEFT JOIN usuario_ext u ON m.remitente_tipo = 'Usuario' AND m.remitente_id = u.id_usuario
            LEFT JOIN operador o ON m.remitente_tipo = 'Operador' AND m.remitente_id = o.id_operador
            WHERE m.id_ticket = %s 
            AND m.deleted_at IS NULL
        """
        
        # Si no se incluyen privados y es usuario, filtrar solo públicos
        if not incluir_privados or tipo_usuario == 'Usuario':
            query += " AND m.tipo_mensaje = 'Publico'"
        
        query += " ORDER BY m.fecha_envio ASC"
        
        return execute_query(query, (id_ticket,), fetch_all=True)
    
    @staticmethod
    def actualizar_mensaje(id_msg, data):
        """
        Actualiza un mensaje existente.
        Solo se puede editar el contenido.
        
        Args:
            id_msg: int
            data: dict con {'contenido': str}
        
        Returns:
            bool: True si se actualizó
        """
        query = """
            UPDATE mensaje 
            SET contenido = %s,
                estado_mensaje = 'Editado',
                fecha_edicion = %s
            WHERE id_msg = %s AND deleted_at IS NULL
        """
        
        params = (
            data['contenido'],
            datetime.now(),
            id_msg
        )
        
        return execute_query(query, params, commit=True)
    
    @staticmethod
    def eliminar_mensaje(id_msg, soft_delete=True):
        """
        Elimina un mensaje (soft delete por defecto).
        
        Args:
            id_msg: int
            soft_delete: bool - Si True, marca como eliminado. Si False, elimina físicamente.
        
        Returns:
            bool: True si se eliminó
        """
        if soft_delete:
            query = """
                UPDATE mensaje 
                SET estado_mensaje = 'Eliminado',
                    deleted_at = %s
                WHERE id_msg = %s
            """
            params = (datetime.now(), id_msg)
        else:
            query = "DELETE FROM mensaje WHERE id_msg = %s"
            params = (id_msg,)
        
        return execute_query(query, params, commit=True)
    
    @staticmethod
    def marcar_como_interno(id_msg):
        """
        Marca un mensaje público como privado (solo visible para operadores).
        
        Args:
            id_msg: int
        
        Returns:
            bool: True si se actualizó
        """
        query = """
            UPDATE mensaje 
            SET tipo_mensaje = 'Privado'
            WHERE id_msg = %s AND deleted_at IS NULL
        """
        
        return execute_query(query, (id_msg,), commit=True)
    
    @staticmethod
    def crear_desde_email(email_data):
        """
        Crea un mensaje desde un email recibido.
        Extrae información del email y crea el mensaje.
        
        Args:
            email_data: dict con {
                'from_email': str,
                'subject': str,
                'body': str,
                'ticket_id': int (puede ser None si es nuevo ticket)
            }
        
        Returns:
            dict: {'id_msg': int, 'id_ticket': int}
        """
        try:
            from flask_app.models.usuario_ext_model import UsuarioExtModel
            from flask_app.config.conexion_login import get_local_db_connection
            from datetime import datetime
            
            # Buscar usuario por email
            usuario = UsuarioExtModel.buscar_por_email(email_data['from_email'])
            
            if not usuario:
                # Crear usuario si no existe
                usuario_data = {
                    'email': email_data['from_email'],
                    'nombre': email_data.get('from_name', email_data['from_email'].split('@')[0]),
                    'existe_flex': 0
                }
                usuario_id = UsuarioExtModel.crear_usuario(usuario_data)
            else:
                usuario_id = usuario['id']
            
            # Crear ticket y mensaje directamente
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            try:
                # Insertar ticket (usando solo columnas que existen)
                cursor.execute("""
                    INSERT INTO ticket 
                    (titulo, fecha_ini, id_estado, id_prioridad, id_usuario)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    email_data['subject'][:100],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    1,  # id_estado = Nuevo
                    3,  # id_prioridad = Media
                    usuario_id
                ))
                ticket_id = cursor.lastrowid

                # Registrar en historial: ticket creado (por usuario externo)
                try:
                    cursor.execute(
                        """
                        INSERT INTO historial_acciones_ticket
                            (id_ticket, id_usuarioext, accion, valor_nuevo, fecha)
                        VALUES
                            (%s, %s, 'Ticket creado', %s, NOW())
                        """,
                        (ticket_id, usuario_id, email_data['subject'][:100]),
                    )
                except Exception:
                    # No bloquear procesamiento de email por fallas en historial
                    import logging
                    logging.exception('No se pudo registrar historial (email): Ticket creado')
                
                # Insertar mensaje
                cursor.execute("""
                    INSERT INTO mensaje 
                    (asunto, contenido, remitente, fecha_envio, id_ticket, id_canal)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    email_data['subject'][:50],
                    email_data['body'][:500],
                    email_data.get('from_name', email_data['from_email'].split('@')[0])[:50],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    ticket_id,
                    1  # id_canal = Email
                ))
                id_msg = cursor.lastrowid

                # Registrar en historial: mensaje público (por usuario externo)
                try:
                    cursor.execute(
                        """
                        INSERT INTO historial_acciones_ticket
                            (id_ticket, id_usuarioext, accion, valor_nuevo, fecha)
                        VALUES
                            (%s, %s, %s, %s, NOW())
                        """,
                        (ticket_id, usuario_id, 'Mensaje publico', email_data['subject'][:50]),
                    )
                except Exception:
                    import logging
                    logging.exception('No se pudo registrar historial (email): Mensaje publico')
                
                conn.commit()
                
                return {
                    'id_msg': id_msg,
                    'id_ticket': ticket_id
                }
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            import traceback
            print(f"Error en crear_desde_email: {str(e)}")
            traceback.print_exc()
            raise
    
    @staticmethod
    def obtener_para_chat(id_ticket, id_operador=None):
        """
        Obtiene mensajes formateados para mostrar en el chat.
        
        Args:
            id_ticket: int
            id_operador: int (opcional) - Si se proporciona, incluye mensajes privados
        
        Returns:
            list de dict con formato para chat
        """
        incluir_privados = id_operador is not None
        tipo_usuario = 'Operador' if id_operador else 'Usuario'
        
        mensajes = MensajeModel.listar_por_ticket(id_ticket, incluir_privados, tipo_usuario)
        
        # Formatear para chat
        chat_mensajes = []
        for msg in mensajes:
            chat_mensajes.append({
                'id': msg['id_msg'],
                'autor': msg['remitente_nombre'],
                'email': msg['remitente_email'],
                'tipo_autor': msg['remitente_tipo'],
                'mensaje': msg['contenido'],
                'fecha': msg['fecha_envio'].isoformat() if isinstance(msg['fecha_envio'], datetime) else msg['fecha_envio'],
                'editado': msg['estado_mensaje'] == 'Editado',
                'fecha_edicion': msg['fecha_edicion'].isoformat() if msg.get('fecha_edicion') else None,
                'es_privado': msg['tipo_mensaje'] == 'Privado',
                'canal': msg['canal_nombre'],
                'adjuntos': msg.get('total_adjuntos', 0)
            })
        
        return chat_mensajes
