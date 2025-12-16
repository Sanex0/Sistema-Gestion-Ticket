from flask_app.config.conexion_login import get_db_connection
from datetime import datetime


class TicketModel:
    
    @staticmethod
    def crear_ticket(data):
        """
        Crea un ticket a partir de un email recibido desde el agente.
        
        Estructura esperada del JSON:
        {
            "titulo": "Se me cayo el perro",
            "es_ticket_externo": 1,
            "es_ticket_privado": 0,
            "fecha_ini": "2025-12-15 11:58:35",
            "fecha_fin": null,
            "id_estado": 1,
            "id_prioridad": 2,
            "id_club": null,
            "usuario_externo": {
                "nombre": "Exequiel Castillo",
                "email": "e.castillocaniu67@gmail.com",
                "telefono": null,
                "run": null
            },
            "mensaje": {
                "asunto": "Se me cayo el perro",
                "contenido": "asfascac",
                "remitente": "Exequiel Castillo",
                "fecha_envio": "2025-12-15 11:58:35",
                "id_canal": 1
            },
            "adjuntos": [],
            "email_metadata": {
                "email_id": "63",
                "to": "Exequiel Castillo <e.castillocaniu67@gmail.com>",
                "date": "Mon, 15 Dec 2025 11:58:17 -0300",
                "reply_to": "e.castillocaniu67@gmail.com"
            }
        }
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 1. Crear o buscar usuario externo
            usuario = data.get('usuario_externo', {})
            id_usuario = TicketModel.get_or_create_usuario(cursor, usuario)
            
            # 2. Crear ticket (según estructura de tabla TICKET)
            fecha_ini = data.get('fecha_ini', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            fecha_fin = data.get('fecha_fin')  # Puede ser null
            
            cursor.execute("""
                INSERT INTO TICKET 
                (titulo, es_ticket_externo, es_ticket_privado, fecha_ini, fecha_fin,
                 id_estado, id_prioridad, id_usuario, id_club)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get('titulo', 'Sin título')[:100],  # VARCHAR(100)
                data.get('es_ticket_externo', 1),
                data.get('es_ticket_privado', 0),
                fecha_ini,
                fecha_fin,
                data.get('id_estado', 1),
                data.get('id_prioridad', 2),
                id_usuario,
                data.get('id_club')
            ))
            id_ticket = cursor.lastrowid
            
            # 3. Crear mensaje asociado al ticket (según estructura de tabla MENSAJE)
            mensaje = data.get('mensaje', {})
            fecha_envio = mensaje.get('fecha_envio', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            cursor.execute("""
                INSERT INTO MENSAJE 
                (asunto, contenido, remitente, fecha_envio, id_ticket, id_canal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                mensaje.get('asunto', data.get('titulo', 'Sin asunto'))[:50],  # VARCHAR(50)
                mensaje.get('contenido', '')[:500],  # VARCHAR(500)
                mensaje.get('remitente', usuario.get('nombre', ''))[:50],  # VARCHAR(50)
                fecha_envio,
                id_ticket,
                mensaje.get('id_canal', 1)  # 1 = Email por defecto
            ))
            id_mensaje = cursor.lastrowid
            
            # 4. Guardar adjuntos si existen (según estructura de tabla ADJUNTO)
            adjuntos = data.get('adjuntos', [])
            for adjunto in adjuntos:
                cursor.execute("""
                    INSERT INTO ADJUNTO 
                    (nom_adj, ruta, id_mensaje)
                    VALUES (%s, %s, %s)
                """, (
                    adjunto.get('nombre', adjunto.get('nom_adj', ''))[:100],  # VARCHAR(100)
                    adjunto.get('url', adjunto.get('ruta', ''))[:500],  # VARCHAR(500)
                    id_mensaje
                ))
            
            conn.commit()
            
            return {
                'success': True, 
                'id_ticket': id_ticket,
                'id_mensaje': id_mensaje,
                'message': 'Ticket creado exitosamente desde email'
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            return {'success': False, 'error': str(e)}
        
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def get_or_create_usuario(cursor, usuario):
        """Busca un usuario por email, si no existe lo crea."""
        email = usuario.get('email', '')
        
        if not email:
            return None
        
        # Buscar si existe por email
        cursor.execute(
            "SELECT id_usuario FROM USUARIO_EXTERNO WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        
        if user:
            return user[0]
        
        # Crear nuevo usuario (según estructura de tabla USUARIO_EXTERNO)
        cursor.execute("""
            INSERT INTO USUARIO_EXTERNO (run, nombre, telefono, email)
            VALUES (%s, %s, %s, %s)
        """, (
            usuario.get('run', '')[:10] if usuario.get('run') else None,  # VARCHAR(10)
            usuario.get('nombre', 'Sin nombre')[:45],  # VARCHAR(45)
            usuario.get('telefono', '')[:15] if usuario.get('telefono') else None,  # VARCHAR(15)
            email[:100]  # VARCHAR(100)
        ))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_tickets(filtros=None):
        """Obtiene lista de tickets con filtros opcionales."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT t.id_ticket, t.titulo, t.es_ticket_externo, t.id_estado, 
                       t.id_prioridad, t.fecha_ini, u.nombre, u.email
                FROM TICKET t
                LEFT JOIN USUARIO_EXTERNO u ON t.id_usuario = u.id_usuario
                ORDER BY t.fecha_ini DESC
                LIMIT 100
            """
            cursor.execute(query)
            tickets = cursor.fetchall()
            
            resultado = []
            for t in tickets:
                resultado.append({
                    'id_ticket': t[0],
                    'titulo': t[1],
                    'es_ticket_externo': t[2],
                    'id_estado': t[3],
                    'id_prioridad': t[4],
                    'fecha_ini': str(t[5]) if t[5] else None,
                    'usuario': {
                        'nombre': t[6],
                        'email': t[7]
                    }
                })
            
            return {'success': True, 'tickets': resultado}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def obtener_ticket_por_id(id_ticket):
        """Obtiene un ticket específico con sus mensajes."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Obtener ticket
            cursor.execute("""
                SELECT t.id_ticket, t.titulo, t.es_ticket_externo, t.id_estado, 
                       t.id_prioridad, t.fecha_ini, u.nombre, u.email
                FROM TICKET t
                LEFT JOIN USUARIO_EXTERNO u ON t.id_usuario = u.id_usuario
                WHERE t.id_ticket = %s
            """, (id_ticket,))
            t = cursor.fetchone()
            
            if not t:
                return {'success': False, 'error': 'Ticket no encontrado'}
            
            # Obtener mensajes del ticket
            cursor.execute("""
                SELECT id_mensaje, asunto, contenido, remitente, fecha_envio, id_canal
                FROM MENSAJE
                WHERE id_ticket = %s
                ORDER BY fecha_envio ASC
            """, (id_ticket,))
            mensajes = cursor.fetchall()
            
            return {
                'success': True,
                'ticket': {
                    'id_ticket': t[0],
                    'titulo': t[1],
                    'es_ticket_externo': t[2],
                    'id_estado': t[3],
                    'id_prioridad': t[4],
                    'fecha_ini': str(t[5]) if t[5] else None,
                    'usuario': {
                        'nombre': t[6],
                        'email': t[7]
                    },
                    'mensajes': [{
                        'id_mensaje': m[0],
                        'asunto': m[1],
                        'contenido': m[2],
                        'remitente': m[3],
                        'fecha_envio': str(m[4]) if m[4] else None,
                        'id_canal': m[5]
                    } for m in mensajes]
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def obtener_solicitudes_pendientes():
        """
        Obtiene tickets pendientes de aceptación (solicitudes nuevas).
        Estado 1 = Pendiente/Nuevo, sin operador asignado.
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT t.id_ticket, t.titulo, t.es_ticket_externo, t.es_ticket_privado,
                       t.fecha_ini, t.id_estado, t.id_prioridad,
                       u.nombre, u.email, u.telefono,
                       e.descripcion as estado_desc,
                       p.descripcion as prioridad_desc
                FROM TICKET t
                LEFT JOIN USUARIO_EXTERNO u ON t.id_usuario = u.id_usuario
                LEFT JOIN ESTADO e ON t.id_estado = e.id_estado
                LEFT JOIN PRIORIDAD p ON t.id_prioridad = p.id_prioridad
                WHERE t.id_estado = 1
                  AND NOT EXISTS (
                      SELECT 1 FROM TICKET_OWNER tw WHERE tw.id_ticket = t.id_ticket
                  )
                ORDER BY t.fecha_ini ASC
            """)
            tickets = cursor.fetchall()
            
            resultado = []
            for t in tickets:
                # Obtener primer mensaje del ticket
                cursor.execute("""
                    SELECT asunto, contenido, remitente, fecha_envio
                    FROM MENSAJE
                    WHERE id_ticket = %s
                    ORDER BY fecha_envio ASC
                    LIMIT 1
                """, (t[0],))
                mensaje = cursor.fetchone()
                
                resultado.append({
                    'id_ticket': t[0],
                    'titulo': t[1],
                    'es_ticket_externo': t[2],
                    'es_ticket_privado': t[3],
                    'fecha_ini': str(t[4]) if t[4] else None,
                    'id_estado': t[5],
                    'id_prioridad': t[6],
                    'estado': t[10],
                    'prioridad': t[11],
                    'usuario': {
                        'nombre': t[7],
                        'email': t[8],
                        'telefono': t[9]
                    },
                    'mensaje': {
                        'asunto': mensaje[0] if mensaje else None,
                        'contenido': mensaje[1] if mensaje else None,
                        'remitente': mensaje[2] if mensaje else None,
                        'fecha_envio': str(mensaje[3]) if mensaje and mensaje[3] else None
                    } if mensaje else None
                })
            
            return {'success': True, 'solicitudes': resultado, 'total': len(resultado)}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def aceptar_solicitud(id_ticket, id_operador):
        """
        Acepta una solicitud: asigna el operador como owner y cambia estado a 'En proceso'.
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar que el ticket existe y está pendiente
            cursor.execute("SELECT id_estado FROM TICKET WHERE id_ticket = %s", (id_ticket,))
            ticket = cursor.fetchone()
            
            if not ticket:
                return {'success': False, 'error': 'Ticket no encontrado'}
            
            # Verificar que no tenga owner ya
            cursor.execute("SELECT id_operador FROM TICKET_OWNER WHERE id_ticket = %s", (id_ticket,))
            if cursor.fetchone():
                return {'success': False, 'error': 'Este ticket ya fue aceptado por otro operador'}
            
            # Asignar operador como owner del ticket
            cursor.execute("""
                INSERT INTO TICKET_OWNER (id_ticket, id_operador)
                VALUES (%s, %s)
            """, (id_ticket, id_operador))
            
            # Cambiar estado a 2 (En proceso/Aceptado)
            cursor.execute("""
                UPDATE TICKET SET id_estado = 2 WHERE id_ticket = %s
            """, (id_ticket,))
            
            # Registrar en histórico
            cursor.execute("""
                INSERT INTO HISTORICO_TICKET (id_owner, id_operador, accion, fecha)
                VALUES (%s, %s, %s, NOW())
            """, (id_ticket, id_operador, 'Solicitud aceptada'))
            
            conn.commit()
            
            return {
                'success': True,
                'message': 'Solicitud aceptada exitosamente',
                'id_ticket': id_ticket,
                'id_operador': id_operador
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            return {'success': False, 'error': str(e)}
        
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def rechazar_solicitud(id_ticket, id_operador, motivo=None):
        """
        Rechaza una solicitud: cambia estado a rechazado.
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar que el ticket existe
            cursor.execute("SELECT id_estado FROM TICKET WHERE id_ticket = %s", (id_ticket,))
            ticket = cursor.fetchone()
            
            if not ticket:
                return {'success': False, 'error': 'Ticket no encontrado'}
            
            # Cambiar estado a rechazado (ej: 4)
            cursor.execute("""
                UPDATE TICKET SET id_estado = 4 WHERE id_ticket = %s
            """, (id_ticket,))
            
            # Registrar en histórico
            accion = f'Solicitud rechazada: {motivo}' if motivo else 'Solicitud rechazada'
            cursor.execute("""
                INSERT INTO HISTORICO_TICKET (id_owner, id_operador, accion, fecha)
                VALUES (%s, %s, %s, NOW())
            """, (id_ticket, id_operador, accion[:300]))
            
            conn.commit()
            
            return {
                'success': True,
                'message': 'Solicitud rechazada',
                'id_ticket': id_ticket
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            return {'success': False, 'error': str(e)}
        
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def obtener_tickets_operador(id_operador):
        """
        Obtiene los tickets asignados a un operador específico.
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT t.id_ticket, t.titulo, t.es_ticket_externo, t.fecha_ini, t.fecha_fin,
                       t.id_estado, t.id_prioridad,
                       u.nombre, u.email,
                       e.descripcion as estado_desc,
                       p.descripcion as prioridad_desc
                FROM TICKET t
                INNER JOIN TICKET_OWNER tw ON t.id_ticket = tw.id_ticket
                LEFT JOIN USUARIO_EXTERNO u ON t.id_usuario = u.id_usuario
                LEFT JOIN ESTADO e ON t.id_estado = e.id_estado
                LEFT JOIN PRIORIDAD p ON t.id_prioridad = p.id_prioridad
                WHERE tw.id_operador = %s
                ORDER BY t.fecha_ini DESC
            """, (id_operador,))
            tickets = cursor.fetchall()
            
            resultado = []
            for t in tickets:
                resultado.append({
                    'id_ticket': t[0],
                    'titulo': t[1],
                    'es_ticket_externo': t[2],
                    'fecha_ini': str(t[3]) if t[3] else None,
                    'fecha_fin': str(t[4]) if t[4] else None,
                    'id_estado': t[5],
                    'id_prioridad': t[6],
                    'estado': t[9],
                    'prioridad': t[10],
                    'usuario': {
                        'nombre': t[7],
                        'email': t[8]
                    }
                })
            
            return {'success': True, 'tickets': resultado, 'total': len(resultado)}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        finally:
            if conn:
                cursor.close()
                conn.close()