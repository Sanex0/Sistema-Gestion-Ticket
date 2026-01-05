from flask_app.config.conexion_login import get_local_db_connection
from datetime import datetime
import logging
import traceback


class TicketModel:
    
    @staticmethod
    def crear(data, operador_actual=None):
        """
            Crea un nuevo ticket y lo asigna a un operador.
        
        Estructura esperada:
        {
            "titulo": "Titulo del ticket",
            "tipo_ticket": "Publico" o "Privado",
            "descripcion": "Descripcion del problema",
            "id_estado": 1 (Nuevo),
            "id_prioridad": 2,
            "id_club": 1,
            "id_sla": 1,
            "id_usuarioext": 1 (opcional, si ya existe usuario),
            "usuario_externo": {
                "nombre": "Juan Perez",
                "email": "juan@example.com",
                "telefono": "+56912345678",
                "rut": "12345678-9"
            }
        }
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # 1. Obtener o crear usuario externo si se proporciona
            id_usuarioext = data.get('id_usuarioext')
            if not id_usuarioext and data.get('usuario_externo'):
                id_usuarioext = TicketModel._get_or_create_usuario_ext(cursor, data['usuario_externo'])
            
            # 2. Crear ticket con columnas reales de la DB
            fecha_ini = data.get('fecha_ini', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            cursor.execute("""
                INSERT INTO ticket 
                (titulo, tipo_ticket, descripcion, fecha_ini, id_estado, id_prioridad, 
                 id_usuarioext, id_club, id_sla)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get('titulo', 'Sin titulo'),
                data.get('tipo_ticket', 'Publico'),
                data.get('descripcion', ''),
                fecha_ini,
                data.get('id_estado', 1),  # Estado: Nuevo
                data.get('id_prioridad', 2),  # Prioridad: Media
                id_usuarioext,
                data.get('id_club', 1),
                data.get('id_sla', 1)
            ))
            id_ticket = cursor.lastrowid
            
            conn.commit()
            logging.info(f'Ticket creado id_ticket={id_ticket} (pre-asignaciones)')
            
            # 3. Asignar ticket a operador
            id_operador_asignado = data.get('id_operador_asignado')
            if id_operador_asignado:
                cursor.execute("""
                    INSERT INTO ticket_operador 
                    (id_operador, id_ticket, rol, fecha_asignacion)
                    VALUES (%s, %s, %s, %s)
                """, (
                    id_operador_asignado,
                    id_ticket,
                    'Owner',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                logging.info(f'Ticket {id_ticket}: asignado a operador {id_operador_asignado} como Owner')
            
            # 4. Si hay operador logeado que crea el ticket, también agregarlo
            if operador_actual:
                id_creator = operador_actual.get('operador_id')
                if id_creator and id_creator != id_operador_asignado:
                    cursor.execute("""
                        INSERT INTO ticket_operador 
                        (id_operador, id_ticket, rol, fecha_asignacion)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        id_creator,
                        id_ticket,
                        'Colaborador',
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    logging.info(f'Ticket {id_ticket}: creador operador {id_creator} agregado como Colaborador')

            # Guardar asignaciones en la base de datos
            try:
                conn.commit()
            except Exception:
                # Si el commit falla, intentar rollback y reportar
                conn.rollback()
                return {'success': False, 'error': 'Error al guardar asignaciones del ticket'}

            return {
                'success': True,
                'id_ticket': id_ticket,
                'message': 'Ticket creado exitosamente'
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    
    @staticmethod
    def _get_or_create_usuario_ext(cursor, usuario_data):
        """Busca un usuario externo por email, si no existe lo crea."""
        email = usuario_data.get('email', '')
        if not email:
            return None
        
        # Buscar usuario existente
        cursor.execute("SELECT id_usuario FROM usuario_ext WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            return user['id_usuario'] if isinstance(user, dict) else user[0]
        
        # Crear nuevo usuario
        cursor.execute("""
            INSERT INTO usuario_ext (rut, nombre, telefono, email, existe_flex)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            usuario_data.get('rut'),
            usuario_data.get('nombre', 'Sin nombre'),
            usuario_data.get('telefono'),
            email,
            0
        ))
        return cursor.lastrowid
    
    @staticmethod
    def get_all(limit=50, offset=0, operador_actual=None):
        """
        Obtiene lista de tickets según permisos del operador.
        - Operador: Solo sus tickets asignados
        - Supervisor: Sus tickets + de subordinados
        - Admin: Todos
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Determinar filtro según rol del operador
            where_clause = "WHERE t.deleted_at IS NULL"
            params = []
            
            if operador_actual:
                # Soportar diferentes formas del payload del token / operador
                id_operador = (
                    operador_actual.get('operador_id')
                    or operador_actual.get('id')
                    or operador_actual.get('id_operador')
                )

                # Rol puede venir como id o como nombre
                rol_id = operador_actual.get('rol_id') or operador_actual.get('id_rol_global')
                rol_nombre = operador_actual.get('rol') or operador_actual.get('rol_nombre')

                # Determinar si es Admin: rol_id == 1 o nombre 'admin'
                is_admin = (rol_id == 1) or (isinstance(rol_nombre, str) and rol_nombre.lower() == 'admin')

                # Si NO es Admin, filtrar
                if not is_admin:
                    # Ver si es supervisor
                    cursor.execute("""
                        SELECT COUNT(*) as es_supervisor FROM miembro_dpto 
                        WHERE id_operador = %s AND rol IN ('Supervisor', 'Jefe')
                    """, (id_operador,))
                    is_supervisor = cursor.fetchone()['es_supervisor'] > 0
                    
                    if is_supervisor:
                        # Supervisor: sus tickets + subordinados
                        where_clause += """
                            AND (
                                EXISTS (SELECT 1 FROM ticket_operador 
                                        WHERE ticket_operador.id_ticket = t.id_ticket 
                                        AND ticket_operador.id_operador = %s)
                                OR EXISTS (
                                    SELECT 1 FROM ticket_operador to2
                                    INNER JOIN miembro_dpto md ON to2.id_operador = md.id_operador
                                    INNER JOIN miembro_dpto md_supervisor ON md.id_depto = md_supervisor.id_depto
                                    WHERE to2.id_ticket = t.id_ticket 
                                    AND md.rol = 'Agente'
                                    AND md_supervisor.id_operador = %s
                                    AND md_supervisor.rol IN ('Supervisor', 'Jefe')
                                )
                            )
                        """
                        params = [id_operador, id_operador]
                    else:
                        # Operador normal: solo sus tickets
                        where_clause += """
                            AND EXISTS (SELECT 1 FROM ticket_operador 
                                       WHERE ticket_operador.id_ticket = t.id_ticket 
                                       AND ticket_operador.id_operador = %s)
                        """
                        params = [id_operador]
            
            # Contar total con filtro
            count_query = f"SELECT COUNT(*) as total FROM ticket t {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Obtener tickets con sus detalles
            query = f"""
                SELECT 
                    t.id_ticket, t.titulo, t.tipo_ticket, t.descripcion,
                    t.fecha_ini, t.fecha_primera_respuesta, t.fecha_resolucion,
                    t.id_estado, t.id_prioridad, t.id_usuarioext, t.id_club, t.id_sla,
                    es.descripcion as estado_desc,
                    pr.descripcion as prioridad_desc,
                    ue.nombre as usuario_nombre,
                    ue.email as usuario_email,
                    cl.nom_club as club_nombre
                FROM ticket t
                LEFT JOIN estado es ON t.id_estado = es.id_estado
                LEFT JOIN prioridad pr ON t.id_prioridad = pr.id_prioridad
                LEFT JOIN usuario_ext ue ON t.id_usuarioext = ue.id_usuario
                LEFT JOIN club cl ON t.id_club = cl.id_club
                {where_clause}
                ORDER BY t.fecha_ini DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()
            
            tickets = []
            for row in rows:
                ticket = {
                    'id_ticket': row['id_ticket'],
                    'titulo': row['titulo'],
                    'tipo_ticket': row['tipo_ticket'],
                    'descripcion': row['descripcion'],
                    'fecha_ini': str(row['fecha_ini']),
                    'id_estado': row['id_estado'],
                    'id_prioridad': row['id_prioridad'],
                    'estado': row['estado_desc'],
                    'prioridad': row['prioridad_desc'],
                    'usuario': {
                        'nombre': row['usuario_nombre'],
                        'email': row['usuario_email']
                    },
                    'club': row['club_nombre']
                }
                tickets.append(ticket)
            
            return {
                'success': True,
                'tickets': tickets,
                'total': total,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            logging.exception('Error en TicketModel.get_all')
            # también incluimos el traceback en la respuesta temporalmente
            tb = traceback.format_exc()
            return {'success': False, 'error': str(e), 'traceback': tb}
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    
    @staticmethod
    def get_by_id(id_ticket):
        """Obtiene un ticket especifico con detalles completos."""
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Obtener ticket con detalles
            query = """
                SELECT 
                    t.id_ticket, t.titulo, t.tipo_ticket, t.descripcion,
                    t.fecha_ini, t.fecha_primera_respuesta, t.fecha_resolucion,
                    t.id_estado, t.id_prioridad, t.id_usuarioext, t.id_club, t.id_sla,
                    es.descripcion as estado_desc,
                    pr.descripcion as prioridad_desc,
                    ue.nombre as usuario_nombre,
                    ue.email as usuario_email,
                    ue.telefono as usuario_telefono,
                    ue.rut as usuario_rut,
                    cl.nom_club as club_nombre,
                    sl.nombre as sla_nombre
                FROM ticket t
                LEFT JOIN estado es ON t.id_estado = es.id_estado
                LEFT JOIN prioridad pr ON t.id_prioridad = pr.id_prioridad
                LEFT JOIN usuario_ext ue ON t.id_usuarioext = ue.id_usuario
                LEFT JOIN club cl ON t.id_club = cl.id_club
                LEFT JOIN sla sl ON t.id_sla = sl.id_sla
                WHERE t.id_ticket = %s AND t.deleted_at IS NULL
            """
            cursor.execute(query, (id_ticket,))
            row = cursor.fetchone()
            
            if not row:
                return {'success': False, 'error': 'Ticket no encontrado', 'code': 404}
            
            # Obtener mensajes del ticket
            msg_query = """
                SELECT 
                    m.id_msg, m.tipo_mensaje, m.asunto, m.contenido,
                    m.remitente_id, m.remitente_tipo, m.estado_mensaje,
                    m.fecha_envio, m.fecha_edicion
                FROM mensaje m
                WHERE m.id_ticket = %s AND m.deleted_at IS NULL
                ORDER BY m.fecha_envio ASC
            """
            cursor.execute(msg_query, (id_ticket,))
            mensajes_rows = cursor.fetchall()
            
            mensajes = []
            for msg_row in mensajes_rows:
                msg = {
                    'id_msg': msg_row['id_msg'] if isinstance(msg_row, dict) else msg_row[0],
                    'tipo_mensaje': msg_row['tipo_mensaje'] if isinstance(msg_row, dict) else msg_row[1],
                    'asunto': msg_row['asunto'] if isinstance(msg_row, dict) else msg_row[2],
                    'contenido': msg_row['contenido'] if isinstance(msg_row, dict) else msg_row[3],
                    'remitente_id': msg_row['remitente_id'] if isinstance(msg_row, dict) else msg_row[4],
                    'remitente_tipo': msg_row['remitente_tipo'] if isinstance(msg_row, dict) else msg_row[5],
                    'estado_mensaje': msg_row['estado_mensaje'] if isinstance(msg_row, dict) else msg_row[6],
                    'fecha_envio': str(msg_row['fecha_envio']) if isinstance(msg_row, dict) else str(msg_row[7])
                }
                mensajes.append(msg)
            
            # Construir respuesta
            ticket = {
                'id_ticket': row['id_ticket'] if isinstance(row, dict) else row[0],
                'titulo': row['titulo'] if isinstance(row, dict) else row[1],
                'tipo_ticket': row['tipo_ticket'] if isinstance(row, dict) else row[2],
                'descripcion': row['descripcion'] if isinstance(row, dict) else row[3],
                'fecha_ini': str(row['fecha_ini']) if isinstance(row, dict) else str(row[4]),
                'id_estado': row['id_estado'] if isinstance(row, dict) else row[7],
                'id_prioridad': row['id_prioridad'] if isinstance(row, dict) else row[8],
                'estado': row['estado_desc'] if isinstance(row, dict) else row[12],
                'prioridad': row['prioridad_desc'] if isinstance(row, dict) else row[13],
                'usuario': {
                    'nombre': row['usuario_nombre'] if isinstance(row, dict) else row[14],
                    'email': row['usuario_email'] if isinstance(row, dict) else row[15],
                    'telefono': row['usuario_telefono'] if isinstance(row, dict) else row[16],
                    'rut': row['usuario_rut'] if isinstance(row, dict) else row[17]
                },
                'club': row['club_nombre'] if isinstance(row, dict) else row[18],
                'sla': row['sla_nombre'] if isinstance(row, dict) else row[19],
                'mensajes': mensajes
            }
            
            return {'success': True, 'ticket': ticket}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass