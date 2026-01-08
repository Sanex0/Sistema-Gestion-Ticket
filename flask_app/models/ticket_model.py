from flask_app.config.conexion_login import get_local_db_connection
from datetime import datetime
import logging
import traceback


class TicketModel:

    @staticmethod
    def _build_visibility_where(cursor, operador_actual):
        """Construye el WHERE de visibilidad de tickets según rol/permisos.

        Retorna: (where_clause, params)
        where_clause incluye el prefijo "WHERE ..." y usa el alias `t`.
        """
        where_clause = "WHERE t.deleted_at IS NULL"
        params = []

        if not operador_actual:
            return where_clause, params

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

        if is_admin:
            return where_clause, params

        # Ver si es supervisor/jefe en algún departamento
        cursor.execute("""
            SELECT COUNT(*) as es_supervisor FROM miembro_dpto
            WHERE id_operador = %s AND rol IN ('Supervisor', 'Jefe')
        """, (id_operador,))
        row = cursor.fetchone()
        es_supervisor_count = row['es_supervisor'] if isinstance(row, dict) else row[0]
        is_supervisor = es_supervisor_count > 0

        if is_supervisor:
            cursor.execute("""
                SELECT md_sup.id_depto
                FROM miembro_dpto md_sup
                WHERE md_sup.id_operador = %s
                  AND md_sup.rol IN ('Supervisor', 'Jefe')
                  AND md_sup.fecha_desasignacion IS NULL
            """, (id_operador,))
            dept_rows = cursor.fetchall() or []
            dept_ids = [
                (r['id_depto'] if isinstance(r, dict) else r[0])
                for r in dept_rows
                if (r['id_depto'] if isinstance(r, dict) else r[0]) is not None
            ]

            if dept_ids:
                placeholders = ','.join(['%s'] * len(dept_ids))
                where_clause += f"""
                    AND (
                        t.id_depto IN ({placeholders})
                        OR EXISTS (
                            SELECT 1 FROM miembro_dpto md_emisor
                            WHERE md_emisor.id_operador = t.id_operador_emisor
                              AND md_emisor.id_depto IN ({placeholders})
                              AND md_emisor.fecha_desasignacion IS NULL
                        )
                        OR (t.id_operador_emisor = %s)
                    )
                """
                params = dept_ids + dept_ids + [id_operador]
            else:
                where_clause += " AND (t.id_operador_emisor = %s) "
                params = [id_operador]
        else:
            # Operador normal: tickets asignados + sin asignar de su depto (NO sus propios tickets sin aceptar)
            where_clause += """
                AND (
                    EXISTS (SELECT 1 FROM ticket_operador
                           WHERE ticket_operador.id_ticket = t.id_ticket
                           AND ticket_operador.id_operador = %s
                           AND ticket_operador.fecha_desasignacion IS NULL)
                    OR (
                        NOT EXISTS (
                            SELECT 1 FROM ticket_operador to_check
                            WHERE to_check.id_ticket = t.id_ticket
                            AND to_check.rol = 'Owner'
                            AND to_check.fecha_desasignacion IS NULL
                        )
                        AND EXISTS (
                            SELECT 1 FROM miembro_dpto md
                            WHERE md.id_operador = %s
                            AND md.id_depto = t.id_depto
                            AND md.fecha_desasignacion IS NULL
                        )
                        AND t.id_operador_emisor != %s
                    )
                    OR (t.id_operador_emisor = %s)
                )
            """
            params = [id_operador, id_operador, id_operador, id_operador]

        return where_clause, params

    @staticmethod
    def get_estadisticas(operador_actual=None):
        """Obtiene estadísticas para KPIs (con scope por permisos)."""
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()

            where_clause, params = TicketModel._build_visibility_where(cursor, operador_actual)

            # Total visible
            cursor.execute(f"SELECT COUNT(*) as total FROM ticket t {where_clause}", params)
            row_total = cursor.fetchone()
            total_tickets = row_total['total'] if isinstance(row_total, dict) else row_total[0]

            # Por estado
            cursor.execute(f"""
                SELECT t.id_estado as id_estado, e.descripcion as estado, COUNT(*) as total
                FROM ticket t
                LEFT JOIN estado e ON t.id_estado = e.id_estado
                {where_clause}
                GROUP BY t.id_estado, e.descripcion
                ORDER BY total DESC
            """, params)
            por_estado = cursor.fetchall() or []

            # Por prioridad
            cursor.execute(f"""
                SELECT t.id_prioridad as id_prioridad, p.descripcion as prioridad, COUNT(*) as total
                FROM ticket t
                LEFT JOIN prioridad p ON t.id_prioridad = p.id_prioridad
                {where_clause}
                GROUP BY t.id_prioridad, p.descripcion
                ORDER BY total DESC
            """, params)
            por_prioridad = cursor.fetchall() or []

            # Por periodo
            cursor.execute(
                f"SELECT COUNT(*) as total FROM ticket t {where_clause} AND DATE(t.fecha_ini) = CURDATE()",
                params
            )
            row_hoy = cursor.fetchone()
            hoy = row_hoy['total'] if isinstance(row_hoy, dict) else row_hoy[0]

            cursor.execute(
                f"SELECT COUNT(*) as total FROM ticket t {where_clause} AND DATE(t.fecha_ini) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)",
                params
            )
            row_semana = cursor.fetchone()
            semana = row_semana['total'] if isinstance(row_semana, dict) else row_semana[0]

            cursor.execute(
                f"SELECT COUNT(*) as total FROM ticket t {where_clause} AND DATE(t.fecha_ini) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)",
                params
            )
            row_mes = cursor.fetchone()
            mes = row_mes['total'] if isinstance(row_mes, dict) else row_mes[0]

            # Mis tickets (asignados como Owner al operador actual)
            mis_tickets = 0
            id_operador = None
            if operador_actual:
                id_operador = (
                    operador_actual.get('operador_id')
                    or operador_actual.get('id')
                    or operador_actual.get('id_operador')
                )
            if id_operador:
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT t.id_ticket) as total
                    FROM ticket t
                    INNER JOIN ticket_operador to1
                        ON to1.id_ticket = t.id_ticket
                       AND to1.rol = 'Owner'
                       AND to1.fecha_desasignacion IS NULL
                    {where_clause}
                    AND to1.id_operador = %s
                """, params + [id_operador])
                row_mis = cursor.fetchone()
                mis_tickets = row_mis['total'] if isinstance(row_mis, dict) else row_mis[0]

            # KPI: abiertos (por defecto todo lo que NO está "Cerrado" id_estado=4)
            cursor.execute(
                f"SELECT COUNT(*) as total FROM ticket t {where_clause} AND t.id_estado != 4",
                params
            )
            row_abiertos = cursor.fetchone()
            tickets_abiertos = row_abiertos['total'] if isinstance(row_abiertos, dict) else row_abiertos[0]

            # KPI: resueltos hoy (usa fecha_resolucion si existe)
            cursor.execute(
                f"SELECT COUNT(*) as total FROM ticket t {where_clause} AND t.fecha_resolucion IS NOT NULL AND DATE(t.fecha_resolucion) = CURDATE()",
                params
            )
            row_resueltos_hoy = cursor.fetchone()
            resueltos_hoy = row_resueltos_hoy['total'] if isinstance(row_resueltos_hoy, dict) else row_resueltos_hoy[0]

            return {
                'success': True,
                'estadisticas': {
                    'total_tickets': total_tickets,
                    'por_estado': por_estado,
                    'por_prioridad': por_prioridad,
                    'por_periodo': {
                        'hoy': hoy,
                        'semana': semana,
                        'mes': mes
                    },
                    'tiempo_resolucion': None,
                    'kpis': {
                        'tickets_abiertos': tickets_abiertos,
                        'nuevos_hoy': hoy,
                        'mis_tickets': mis_tickets,
                        'total_tickets': total_tickets,
                        'resueltos_hoy': resueltos_hoy,
                        'satisfaccion_pct': None
                    }
                }
            }

        except Exception as e:
            logging.exception('Error en TicketModel.get_estadisticas')
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
            
            # 2. Crear ticket con columnas reales de la DB (incluye emisor y departamento)
            fecha_ini = data.get('fecha_ini', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            id_operador_emisor = (
                operador_actual.get('operador_id')
                or operador_actual.get('id_operador')
                or operador_actual.get('id')
            ) if operador_actual else None
            id_depto = data.get('id_depto')  # Departamento al que va dirigido el ticket
            
            cursor.execute("""
                INSERT INTO ticket 
                (titulo, tipo_ticket, descripcion, fecha_ini, id_estado, id_prioridad, 
                 id_usuarioext, id_club, id_sla, id_operador_emisor, id_depto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get('titulo', 'Sin titulo'),
                data.get('tipo_ticket', 'Publico'),
                data.get('descripcion', ''),
                fecha_ini,
                data.get('id_estado', 1),  # Estado: Nuevo
                data.get('id_prioridad', 2),  # Prioridad: Media
                id_usuarioext,
                data.get('id_club', 1),
                data.get('id_sla', 1),
                id_operador_emisor,  # Quien crea el ticket
                id_depto  # Departamento destino
            ))
            id_ticket = cursor.lastrowid

            # Registrar en historial (creación)
            try:
                titulo_ticket_raw = data.get('titulo', 'Sin titulo')
                titulo_ticket = (str(titulo_ticket_raw) if titulo_ticket_raw is not None else 'Sin titulo')[:100]
                if id_operador_emisor:
                    cursor.execute(
                        """
                        INSERT INTO historial_acciones_ticket
                            (id_ticket, id_operador, accion, valor_nuevo, fecha)
                        VALUES
                            (%s, %s, 'Ticket creado', %s, NOW())
                        """,
                        (id_ticket, id_operador_emisor, titulo_ticket),
                    )
                elif id_usuarioext:
                    cursor.execute(
                        """
                        INSERT INTO historial_acciones_ticket
                            (id_ticket, id_usuarioext, accion, valor_nuevo, fecha)
                        VALUES
                            (%s, %s, 'Ticket creado', %s, NOW())
                        """,
                        (id_ticket, id_usuarioext, titulo_ticket),
                    )
            except Exception:
                # Nunca bloquear la creación del ticket por historial
                logging.exception('No se pudo registrar historial: Ticket creado')

            # Registrar en historial (ticket recibido por depto destino)
            # Nota: este evento permite que el depto receptor vea un hito explícito.
            try:
                if id_depto:
                    valor_recibido = str(id_depto)[:100]
                    if id_operador_emisor:
                        cursor.execute(
                            """
                            INSERT INTO historial_acciones_ticket
                                (id_ticket, id_operador, accion, valor_nuevo, fecha)
                            VALUES
                                (%s, %s, 'Ticket recibido', %s, NOW())
                            """,
                            (id_ticket, id_operador_emisor, valor_recibido),
                        )
                    elif id_usuarioext:
                        cursor.execute(
                            """
                            INSERT INTO historial_acciones_ticket
                                (id_ticket, id_usuarioext, accion, valor_nuevo, fecha)
                            VALUES
                                (%s, %s, 'Ticket recibido', %s, NOW())
                            """,
                            (id_ticket, id_usuarioext, valor_recibido),
                        )
            except Exception:
                logging.exception('No se pudo registrar historial: Ticket recibido')
            
            # 3. Asignar ticket a operador SOLO si se especifica explícitamente
            # Por defecto, tickets quedan SIN ASIGNAR (Sistema de Escalación)
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
            else:
                logging.info(f'Ticket {id_ticket}: creado SIN ASIGNAR (pendiente de tomar)')
            
            # 4. El emisor ya está registrado en id_operador_emisor
            # No necesitamos agregarlo como Colaborador en ticket_operador
            # El emisor SIEMPRE verá sus tickets gracias a la columna id_operador_emisor

            # Guardar ticket + historial + asignaciones
            conn.commit()

            logging.info(f'Ticket creado id_ticket={id_ticket} por operador {id_operador_emisor} para depto {id_depto}')

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
            where_clause, params = TicketModel._build_visibility_where(cursor, operador_actual)
            
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
                    t.id_operador_emisor, t.id_depto as id_depto_ticket,
                    es.descripcion as estado_desc,
                    pr.descripcion as prioridad_desc,
                    ue.nombre as usuario_nombre,
                    ue.email as usuario_email,
                    cl.nom_club as club_nombre,
                    op_emisor.nombre as emisor_nombre,
                    (SELECT to1.id_operador FROM ticket_operador to1 
                     WHERE to1.id_ticket = t.id_ticket AND to1.rol = 'Owner' 
                     AND to1.fecha_desasignacion IS NULL
                     LIMIT 1) as id_operador,
                    (SELECT op.nombre FROM ticket_operador to2 
                     INNER JOIN operador op ON to2.id_operador = op.id_operador
                     WHERE to2.id_ticket = t.id_ticket AND to2.rol = 'Owner'
                     AND to2.fecha_desasignacion IS NULL
                     LIMIT 1) as operador_nombre,
                    (SELECT COUNT(*) FROM mensaje m_check
                     WHERE m_check.id_ticket = t.id_ticket 
                     AND m_check.remitente_tipo = 'Operador'
                     AND m_check.remitente_id = (
                         SELECT to1.id_operador FROM ticket_operador to1 
                         WHERE to1.id_ticket = t.id_ticket AND to1.rol = 'Owner'
                         AND to1.fecha_desasignacion IS NULL
                         LIMIT 1
                     )
                     AND m_check.deleted_at IS NULL
                    ) as operador_tiene_mensajes,
                    (SELECT m.remitente_id FROM mensaje m
                     WHERE m.id_ticket = t.id_ticket AND m.remitente_tipo = 'Operador'
                     ORDER BY m.fecha_envio ASC LIMIT 1) as id_operador_remitente,
                    (SELECT op2.nombre FROM mensaje m2
                     INNER JOIN operador op2 ON m2.remitente_id = op2.id_operador
                     WHERE m2.id_ticket = t.id_ticket AND m2.remitente_tipo = 'Operador'
                     ORDER BY m2.fecha_envio ASC LIMIT 1) as remitente_nombre,
                    (SELECT md.id_depto FROM ticket_operador to3
                     INNER JOIN miembro_dpto md ON to3.id_operador = md.id_operador
                     WHERE to3.id_ticket = t.id_ticket AND to3.rol = 'Owner' 
                     AND md.fecha_desasignacion IS NULL
                     LIMIT 1) as id_depto_owner
                FROM ticket t
                LEFT JOIN estado es ON t.id_estado = es.id_estado
                LEFT JOIN prioridad pr ON t.id_prioridad = pr.id_prioridad
                LEFT JOIN usuario_ext ue ON t.id_usuarioext = ue.id_usuario
                LEFT JOIN club cl ON t.id_club = cl.id_club
                LEFT JOIN operador op_emisor ON t.id_operador_emisor = op_emisor.id_operador
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
                    'id_usuarioext': row['id_usuarioext'],
                    'id_operador': row['id_operador'],
                    'id_operador_remitente': row['id_operador_remitente'],
                    'id_operador_emisor': row['id_operador_emisor'],
                    # Departamento destino del ticket (para filtros)
                    'id_depto': row.get('id_depto_ticket'),
                    # Departamento del Owner actual (informativo)
                    'id_depto_owner': row.get('id_depto_owner'),
                    'estado': row['estado_desc'],
                    'prioridad': row['prioridad_desc'],
                    'usuario': {
                        'nombre': row['usuario_nombre'],
                        'email': row['usuario_email']
                    },
                    'operador_nombre': row['operador_nombre'],
                    'operador_aceptado': row.get('operador_tiene_mensajes', 0) > 0,
                    'remitente_nombre': row['remitente_nombre'],
                    'emisor_nombre': row['emisor_nombre'],
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
            import pymysql.cursors
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Obtener ticket con detalles
            query = """
                SELECT 
                    t.id_ticket, t.titulo, t.tipo_ticket, t.descripcion,
                    t.fecha_ini, t.fecha_primera_respuesta, t.fecha_resolucion,
                    t.id_estado, t.id_prioridad, t.id_usuarioext, t.id_club, t.id_sla,
                    t.id_operador_emisor,
                    t.id_depto as id_depto_ticket,
                    es.descripcion as estado_desc,
                    pr.descripcion as prioridad_desc,
                    ue.nombre as usuario_nombre,
                    ue.email as usuario_email,
                    ue.telefono as usuario_telefono,
                    ue.rut as usuario_rut,
                    cl.nom_club as club_nombre,
                    sl.nombre as sla_nombre,
                    op_emisor.nombre as emisor_nombre,
                    (SELECT to1.id_operador FROM ticket_operador to1 
                     WHERE to1.id_ticket = t.id_ticket AND to1.rol = 'Owner' 
                     AND to1.fecha_desasignacion IS NULL
                     LIMIT 1) as id_operador,
                    (SELECT op.nombre FROM ticket_operador to2 
                     INNER JOIN operador op ON to2.id_operador = op.id_operador
                     WHERE to2.id_ticket = t.id_ticket AND to2.rol = 'Owner'
                     AND to2.fecha_desasignacion IS NULL
                     LIMIT 1) as operador_nombre
                FROM ticket t
                LEFT JOIN estado es ON t.id_estado = es.id_estado
                LEFT JOIN prioridad pr ON t.id_prioridad = pr.id_prioridad
                LEFT JOIN usuario_ext ue ON t.id_usuarioext = ue.id_usuario
                LEFT JOIN club cl ON t.id_club = cl.id_club
                LEFT JOIN sla sl ON t.id_sla = sl.id_sla
                LEFT JOIN operador op_emisor ON t.id_operador_emisor = op_emisor.id_operador
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
                'id_operador_emisor': row.get('id_operador_emisor') if isinstance(row, dict) else row[12],
                'id_operador': row.get('id_operador') if isinstance(row, dict) else row[23],
                'operador_nombre': row.get('operador_nombre') if isinstance(row, dict) else row[24],
                'emisor_nombre': row.get('emisor_nombre') if isinstance(row, dict) else row[22],
                'id_depto': row.get('id_depto_ticket') if isinstance(row, dict) else row[13],
                'estado': row['estado_desc'] if isinstance(row, dict) else row[14],
                'prioridad': row['prioridad_desc'] if isinstance(row, dict) else row[15],
                'usuario': {
                    'nombre': row['usuario_nombre'] if isinstance(row, dict) else row[16],
                    'email': row['usuario_email'] if isinstance(row, dict) else row[17],
                    'telefono': row['usuario_telefono'] if isinstance(row, dict) else row[18],
                    'rut': row['usuario_rut'] if isinstance(row, dict) else row[19]
                },
                'club': row['club_nombre'] if isinstance(row, dict) else row[20],
                'sla': row['sla_nombre'] if isinstance(row, dict) else row[21],
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
    
    @staticmethod
    def cambiar_estado(ticket_id, nuevo_estado_id, operador_id):
        """
        Cambia el estado de un ticket.
        
        Args:
            ticket_id: ID del ticket
            nuevo_estado_id: Nuevo estado
            operador_id: ID del operador que realiza el cambio
        
        Returns:
            bool: True si se actualizó correctamente
        """
        conn = None
        cursor = None
        try:
            import pymysql.cursors
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Obtener el estado anterior
            cursor.execute("""
                SELECT t.id_estado, t.fecha_resolucion, e.descripcion as estado_anterior
                FROM ticket t
                LEFT JOIN estado e ON t.id_estado = e.id_estado
                WHERE t.id_ticket = %s
            """, (ticket_id,))
            ticket_actual = cursor.fetchone()
            
            if not ticket_actual:
                return False
                
            estado_anterior_id = ticket_actual['id_estado']
            estado_anterior_nombre = ticket_actual['estado_anterior']

            fecha_resolucion_actual = ticket_actual.get('fecha_resolucion')

            # Si no hay cambio real, no registrar historial
            try:
                if int(estado_anterior_id) == int(nuevo_estado_id):
                    # Backfill: tickets legacy en Resuelto/Cerrado sin fecha_resolucion
                    try:
                        nuevo_estado_int = int(nuevo_estado_id)
                    except Exception:
                        nuevo_estado_int = None

                    if nuevo_estado_int in (3, 4) and fecha_resolucion_actual is None:
                        cursor.execute(
                            """
                            UPDATE ticket
                            SET fecha_resolucion = NOW()
                            WHERE id_ticket = %s AND fecha_resolucion IS NULL
                            """,
                            (ticket_id,),
                        )
                        conn.commit()
                    return True
            except Exception:
                pass
            
            # Obtener nombre del nuevo estado
            cursor.execute("""
                SELECT descripcion FROM estado WHERE id_estado = %s
            """, (nuevo_estado_id,))
            nuevo_estado = cursor.fetchone()
            nuevo_estado_nombre = nuevo_estado['descripcion'] if nuevo_estado else str(nuevo_estado_id)

            # Actualizar estado del ticket + fecha_resolucion (para KPIs)
            try:
                nuevo_estado_int = int(nuevo_estado_id)
            except Exception:
                nuevo_estado_int = None
            try:
                estado_anterior_int = int(estado_anterior_id)
            except Exception:
                estado_anterior_int = None

            # Regla de fecha_resolucion:
            # - Al pasar a Resuelto(3) o Cerrado(4): fecha_resolucion = NOW()
            # - Al reabrir (salir de 3/4 hacia otro estado): fecha_resolucion = NULL
            if nuevo_estado_int in (3, 4):
                cursor.execute("""
                    UPDATE ticket
                    SET id_estado = %s,
                        fecha_resolucion = NOW()
                    WHERE id_ticket = %s
                """, (nuevo_estado_id, ticket_id))
            elif estado_anterior_int in (3, 4):
                cursor.execute("""
                    UPDATE ticket
                    SET id_estado = %s,
                        fecha_resolucion = NULL
                    WHERE id_ticket = %s
                """, (nuevo_estado_id, ticket_id))
            else:
                cursor.execute("""
                    UPDATE ticket
                    SET id_estado = %s
                    WHERE id_ticket = %s
                """, (nuevo_estado_id, ticket_id))
            
            # Registrar en historial
            cursor.execute("""
                INSERT INTO historial_acciones_ticket 
                (id_ticket, id_operador, accion, valor_anterior, valor_nuevo)
                VALUES (%s, %s, 'Cambio de estado', %s, %s)
            """, (ticket_id, operador_id, estado_anterior_nombre, nuevo_estado_nombre))
            
            conn.commit()
            
            logging.info(f"Estado del ticket #{ticket_id} cambiado a {nuevo_estado_id} por operador {operador_id}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error al cambiar estado del ticket #{ticket_id}: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def cambiar_prioridad(ticket_id, nueva_prioridad_id, operador_id):
        """
        Cambia la prioridad de un ticket.
        
        Args:
            ticket_id: ID del ticket
            nueva_prioridad_id: Nueva prioridad
            operador_id: ID del operador que realiza el cambio
        
        Returns:
            bool: True si se actualizó correctamente
        """
        conn = None
        cursor = None
        try:
            import pymysql.cursors
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Obtener la prioridad anterior
            cursor.execute("""
                SELECT t.id_prioridad, p.descripcion as prioridad_anterior
                FROM ticket t
                LEFT JOIN prioridad p ON t.id_prioridad = p.id_prioridad
                WHERE t.id_ticket = %s
            """, (ticket_id,))
            ticket_actual = cursor.fetchone()
            
            if not ticket_actual:
                return False
                
            prioridad_anterior_id = ticket_actual['id_prioridad']
            prioridad_anterior_nombre = ticket_actual['prioridad_anterior']

            # Si no hay cambio real, no registrar historial
            try:
                if int(prioridad_anterior_id) == int(nueva_prioridad_id):
                    return True
            except Exception:
                pass
            
            # Obtener nombre de la nueva prioridad
            cursor.execute("""
                SELECT descripcion FROM prioridad WHERE id_prioridad = %s
            """, (nueva_prioridad_id,))
            nueva_prioridad = cursor.fetchone()
            nueva_prioridad_nombre = nueva_prioridad['descripcion'] if nueva_prioridad else str(nueva_prioridad_id)
            
            # Actualizar prioridad del ticket
            cursor.execute("""
                UPDATE ticket 
                SET id_prioridad = %s
                WHERE id_ticket = %s
            """, (nueva_prioridad_id, ticket_id))
            
            # Registrar en historial
            cursor.execute("""
                INSERT INTO historial_acciones_ticket 
                (id_ticket, id_operador, accion, valor_anterior, valor_nuevo)
                VALUES (%s, %s, 'Cambio de prioridad', %s, %s)
            """, (ticket_id, operador_id, prioridad_anterior_nombre, nueva_prioridad_nombre))
            
            conn.commit()
            
            logging.info(f"Prioridad del ticket #{ticket_id} cambiada a {nueva_prioridad_id} por operador {operador_id}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error al cambiar prioridad del ticket #{ticket_id}: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def verificar_y_actualizar_estados_automaticos():
        """
        Verifica y actualiza automáticamente los estados de tickets según reglas de negocio:
        - Tickets en "Nuevo" por más de 1 hora sin respuesta → cambian a "Pendiente"
        
        Returns:
            dict: Resultado de la operación con cantidad de tickets actualizados
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Buscar tickets en estado "Nuevo" (1) con más de 1 hora sin respuesta
            cursor.execute("""
                SELECT t.id_ticket, t.fecha_ini,
                       (SELECT COUNT(*) FROM mensaje m 
                        WHERE m.id_ticket = t.id_ticket 
                        AND m.deleted_at IS NULL) as total_mensajes
                FROM ticket t
                WHERE t.id_estado = 1
                AND t.deleted_at IS NULL
                AND TIMESTAMPDIFF(HOUR, t.fecha_ini, NOW()) >= 1
            """)
            
            tickets_vencidos = cursor.fetchall()
            tickets_actualizados = 0
            
            for ticket in tickets_vencidos:
                ticket_id = ticket[0] if not isinstance(ticket, dict) else ticket['id_ticket']
                total_mensajes = ticket[2] if not isinstance(ticket, dict) else ticket['total_mensajes']
                
                # Si no tiene mensajes, cambiar a "Pendiente" (5)
                if total_mensajes == 0:
                    cursor.execute("""
                        UPDATE ticket 
                        SET id_estado = 5
                        WHERE id_ticket = %s
                    """, (ticket_id,))
                    
                    tickets_actualizados += 1
                    logging.info(f"Ticket #{ticket_id} cambiado automáticamente de 'Nuevo' a 'Pendiente'")
            
            conn.commit()
            
            return {
                'success': True,
                'tickets_actualizados': tickets_actualizados,
                'message': f'{tickets_actualizados} tickets actualizados automáticamente'
            }
            
        except Exception as e:
            logging.error(f"Error al actualizar estados automáticos: {str(e)}")
            if conn:
                conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    @staticmethod
    def obtener_historial_ticket(id_ticket):
        """
        Obtiene el historial completo de acciones de un ticket
        """
        conn = None
        cursor = None
        try:
            import pymysql.cursors
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            query = """
                SELECT 
                    h.id_historial_ticket,
                    h.accion,
                    h.valor_anterior,
                    h.valor_nuevo,
                    h.fecha,
                    o.nombre as operador_nombre,
                    u.nombre as usuario_nombre
                FROM historial_acciones_ticket h
                LEFT JOIN operador o ON h.id_operador = o.id_operador
                LEFT JOIN usuario_ext u ON h.id_usuarioext = u.id_usuario
                WHERE h.id_ticket = %s
                ORDER BY h.fecha DESC
            """
            
            cursor.execute(query, (id_ticket,))
            historial = cursor.fetchall()
            
            # Formatear fechas
            for item in historial:
                if item['fecha']:
                    item['fecha'] = item['fecha'].strftime('%Y-%m-%d %H:%M:%S')
                    
                # Determinar quién realizó la acción
                item['realizado_por'] = item['operador_nombre'] or item['usuario_nombre'] or 'Sistema'
            
            return historial
            
        except Exception as e:
            logging.error(f"Error al obtener historial del ticket {id_ticket}: {str(e)}")
            logging.error(traceback.format_exc())
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def get_emisores_por_contexto(operador_actual):
        """
        Obtiene lista única de emisores según el contexto del operador.
        
        - Admin: Todos los emisores
        - Supervisor: Emisores de tickets en sus departamentos o asignados a sus subordinados
        - Agente: Emisores de tickets asignados a él
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Extraer id del operador
            id_operador = (
                operador_actual.get('operador_id') or
                operador_actual.get('id') or
                operador_actual.get('id_operador')
            )
            
            # Determinar rol
            rol_id = operador_actual.get('rol_id') or operador_actual.get('id_rol_global')
            rol_nombre = operador_actual.get('rol') or operador_actual.get('rol_nombre')
            is_admin = (rol_id == 1) or (isinstance(rol_nombre, str) and rol_nombre.lower() == 'admin')
            
            if is_admin:
                # Admin: Todos los emisores únicos desde ticket.id_operador_emisor
                query = """
                    SELECT DISTINCT o.id_operador, o.nombre, o.email
                    FROM operador o
                    INNER JOIN ticket t ON o.id_operador = t.id_operador_emisor
                    WHERE t.deleted_at IS NULL
                      AND o.deleted_at IS NULL
                    ORDER BY o.nombre
                """
                cursor.execute(query)
            else:
                # Ver si es supervisor
                cursor.execute("""
                    SELECT COUNT(*) as es_supervisor FROM miembro_dpto 
                    WHERE id_operador = %s AND rol IN ('Supervisor', 'Jefe')
                      AND fecha_desasignacion IS NULL
                """, (id_operador,))
                is_supervisor = cursor.fetchone()['es_supervisor'] > 0
                
                if is_supervisor:
                    # Supervisor: Emisores de tickets visibles para el supervisor
                    query = """
                        SELECT DISTINCT o.id_operador, o.nombre, o.email
                        FROM operador o
                        INNER JOIN ticket t ON o.id_operador = t.id_operador_emisor
                        WHERE t.deleted_at IS NULL
                        AND o.deleted_at IS NULL
                        AND (
                            -- Ticket asignado al supervisor
                            EXISTS (SELECT 1 FROM ticket_operador to1 WHERE to1.id_ticket = t.id_ticket AND to1.id_operador = %s AND to1.fecha_desasignacion IS NULL)
                            OR
                            -- Ticket asignado a subordinado
                            EXISTS (
                                SELECT 1 FROM ticket_operador to2
                                INNER JOIN miembro_dpto md_sub ON to2.id_operador = md_sub.id_operador
                                INNER JOIN miembro_dpto md_sup ON md_sub.id_depto = md_sup.id_depto
                                WHERE to2.id_ticket = t.id_ticket
                                AND md_sup.id_operador = %s
                                AND md_sup.rol IN ('Supervisor', 'Jefe')
                                AND md_sup.fecha_desasignacion IS NULL
                                AND md_sub.fecha_desasignacion IS NULL
                                AND to2.fecha_desasignacion IS NULL
                            )
                            OR
                            -- Ticket sin asignar en departamento del supervisor
                            (
                                NOT EXISTS (SELECT 1 FROM ticket_operador to3 WHERE to3.id_ticket = t.id_ticket AND to3.rol = 'Owner' AND to3.fecha_desasignacion IS NULL)
                                AND EXISTS (
                                    SELECT 1 FROM miembro_dpto md_sup2
                                    WHERE md_sup2.id_depto = t.id_depto
                                    AND md_sup2.id_operador = %s
                                    AND md_sup2.rol IN ('Supervisor', 'Jefe')
                                    AND md_sup2.fecha_desasignacion IS NULL
                                )
                            )
                        )
                        ORDER BY o.nombre
                    """
                    cursor.execute(query, (id_operador, id_operador, id_operador))
                else:
                    # Agente: Emisores de tickets asignados a él o creados por él
                    query = """
                        SELECT DISTINCT o.id_operador, o.nombre, o.email
                        FROM operador o
                        INNER JOIN ticket t ON o.id_operador = t.id_operador_emisor
                        WHERE t.deleted_at IS NULL
                        AND o.deleted_at IS NULL
                        AND (
                            -- Ticket asignado al agente
                            EXISTS (SELECT 1 FROM ticket_operador to1 WHERE to1.id_ticket = t.id_ticket AND to1.id_operador = %s AND to1.rol = 'Owner' AND to1.fecha_desasignacion IS NULL)
                            OR
                            -- Ticket creado por el agente
                            t.id_operador_emisor = %s
                        )
                        ORDER BY o.nombre
                    """
                    cursor.execute(query, (id_operador, id_operador))
            
            emisores = cursor.fetchall()
            
            return {
                'success': True,
                'emisores': emisores
            }
            
        except Exception as e:
            logging.exception('Error en TicketModel.get_emisores_por_contexto')
            return {'success': False, 'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def get_receptores_por_contexto(operador_actual):
        """
        Obtiene lista única de receptores (owners) según el contexto del operador.
        
        - Admin: Todos los receptores
        - Supervisor: Receptores de sus departamentos
        - Agente: Receptores de tickets donde él es emisor u owner
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Extraer id del operador
            id_operador = (
                operador_actual.get('operador_id') or
                operador_actual.get('id') or
                operador_actual.get('id_operador')
            )
            
            # Determinar rol
            rol_id = operador_actual.get('rol_id') or operador_actual.get('id_rol_global')
            rol_nombre = operador_actual.get('rol') or operador_actual.get('rol_nombre')
            is_admin = (rol_id == 1) or (isinstance(rol_nombre, str) and rol_nombre.lower() == 'admin')
            
            if is_admin:
                # Admin: Todos los receptores únicos
                query = """
                    SELECT DISTINCT o.id_operador, o.nombre, o.email
                    FROM operador o
                    INNER JOIN ticket_operador to1 ON o.id_operador = to1.id_operador
                    WHERE to1.rol = 'Owner'
                      AND to1.fecha_desasignacion IS NULL
                      AND o.deleted_at IS NULL
                    ORDER BY o.nombre
                """
                cursor.execute(query)
            else:
                # Ver si es supervisor
                cursor.execute("""
                    SELECT COUNT(*) as es_supervisor FROM miembro_dpto 
                    WHERE id_operador = %s AND rol IN ('Supervisor', 'Jefe')
                      AND fecha_desasignacion IS NULL
                """, (id_operador,))
                is_supervisor = cursor.fetchone()['es_supervisor'] > 0
                
                if is_supervisor:
                    # Supervisor: Receptores de sus departamentos
                    query = """
                        SELECT DISTINCT o.id_operador, o.nombre, o.email
                        FROM operador o
                        INNER JOIN ticket_operador to1 ON o.id_operador = to1.id_operador
                        INNER JOIN miembro_dpto md ON o.id_operador = md.id_operador
                        INNER JOIN miembro_dpto md_supervisor ON md.id_depto = md_supervisor.id_depto
                        WHERE to1.rol = 'Owner'
                          AND md_supervisor.id_operador = %s
                          AND md_supervisor.rol IN ('Supervisor', 'Jefe')
                          AND md_supervisor.fecha_desasignacion IS NULL
                          AND md.fecha_desasignacion IS NULL
                          AND to1.fecha_desasignacion IS NULL
                          AND o.deleted_at IS NULL
                        ORDER BY o.nombre
                    """
                    cursor.execute(query, (id_operador,))
                else:
                    # Agente: Receptores (Owner) únicos de tickets donde él participa.
                    # Importante: un agente puede ser emisor de tickets asignados a otros.
                    query = """
                        SELECT DISTINCT o.id_operador, o.nombre, o.email
                        FROM operador o
                        INNER JOIN ticket_operador to1
                            ON o.id_operador = to1.id_operador
                           AND to1.rol = 'Owner'
                           AND to1.fecha_desasignacion IS NULL
                        INNER JOIN ticket t
                            ON t.id_ticket = to1.id_ticket
                           AND t.deleted_at IS NULL
                        WHERE o.deleted_at IS NULL
                          AND (
                              t.id_operador_emisor = %s
                              OR to1.id_operador = %s
                          )
                        ORDER BY o.nombre
                    """
                    cursor.execute(query, (id_operador, id_operador))
            
            receptores = cursor.fetchall()
            
            return {
                'success': True,
                'receptores': receptores
            }
            
        except Exception as e:
            logging.exception('Error en TicketModel.get_receptores_por_contexto')
            return {'success': False, 'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()    
    @staticmethod
    def tomar_ticket(id_ticket, operador_actual):
        """
        Permite a un operador tomar (auto-asignarse) un ticket sin asignar.
        Solo puede tomar tickets de su departamento.
        
        Args:
            id_ticket: ID del ticket a tomar
            operador_actual: Diccionario con operador_id del operador que toma el ticket
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            id_operador = operador_actual.get('operador_id')
            
            # 1. Verificar que el ticket existe y no está eliminado
            cursor.execute("""
                SELECT id_ticket, id_estado, titulo, id_depto
                FROM ticket 
                WHERE id_ticket = %s AND deleted_at IS NULL
            """, (id_ticket,))
            
            ticket = cursor.fetchone()
            if not ticket:
                return {'success': False, 'error': 'Ticket no encontrado'}
            
            # 2. Verificar que el ticket NO tiene Owner actual
            cursor.execute("""
                SELECT id_operador 
                FROM ticket_operador
                WHERE id_ticket = %s 
                  AND rol = 'Owner'
                  AND fecha_desasignacion IS NULL
            """, (id_ticket,))
            
            owner_actual = cursor.fetchone()
            if owner_actual:
                return {'success': False, 'error': 'Este ticket ya está asignado a otro operador'}
            
            # 3. Verificar que el operador pertenece al departamento del ticket
            id_depto_ticket = ticket['id_depto'] if isinstance(ticket, dict) else ticket[3]
            if not id_depto_ticket:
                return {'success': False, 'error': 'Ticket sin departamento asignado'}

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM miembro_dpto
                WHERE id_operador = %s
                  AND id_depto = %s
                  AND fecha_desasignacion IS NULL
            """, (id_operador, id_depto_ticket))

            result = cursor.fetchone()
            count = result['count'] if isinstance(result, dict) else result[0]
            if count == 0:
                return {'success': False, 'error': 'No tiene permisos para tomar tickets de este departamento'}
            
            # 4. Asignar el ticket al operador como Owner
            cursor.execute("""
                INSERT INTO ticket_operador 
                (id_operador, id_ticket, rol, fecha_asignacion)
                VALUES (%s, %s, 'Owner', NOW())
            """, (id_operador, id_ticket))
            
            # 5. Registrar en historial
            cursor.execute("""
                INSERT INTO historial_acciones_ticket
                (id_ticket, id_operador, accion, valor_anterior, valor_nuevo, fecha)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (
                id_ticket,
                id_operador,
                'asignacion',
                'Sin asignar',
                f'Asignado a operador {id_operador}'
            ))
            
            conn.commit()
            logging.info(f'Ticket {id_ticket} tomado por operador {id_operador}')
            
            return {
                'success': True,
                'message': 'Ticket asignado exitosamente',
                'id_ticket': id_ticket
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.exception(f'Error en tomar_ticket id_ticket={id_ticket}')
            return {'success': False, 'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def _is_admin(operador_actual):
        rol = operador_actual.get('rol')
        return isinstance(rol, str) and rol.lower() == 'admin'

    @staticmethod
    def get_acl_info(id_ticket):
        """Información mínima del ticket para validaciones de acceso/escritura."""
        import pymysql.cursors
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT
                    t.id_ticket,
                                        t.titulo,
                    t.id_estado,
                    t.id_operador_emisor,
                    t.id_depto as id_depto_ticket,
                    (SELECT to1.id_operador
                     FROM ticket_operador to1
                     WHERE to1.id_ticket = t.id_ticket
                       AND to1.rol = 'Owner'
                       AND to1.fecha_desasignacion IS NULL
                     LIMIT 1) as id_operador_owner
                FROM ticket t
                WHERE t.id_ticket = %s AND t.deleted_at IS NULL
            """, (id_ticket,))
            return cursor.fetchone()
        except Exception:
            logging.exception('Error en TicketModel.get_acl_info')
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def operador_puede_ver_ticket(id_ticket, operador_actual):
        """Valida si el operador puede ver el ticket (para mensajes/adjuntos)."""
        import pymysql.cursors

        if TicketModel._is_admin(operador_actual):
            return True

        id_operador = operador_actual.get('operador_id')
        if not id_operador:
            return False

        info = TicketModel.get_acl_info(id_ticket)
        if not info:
            return False

        # Emisor siempre puede ver sus tickets
        if info.get('id_operador_emisor') and str(info.get('id_operador_emisor')) == str(id_operador):
            return True

        # Owner puede ver
        if info.get('id_operador_owner') and str(info.get('id_operador_owner')) == str(id_operador):
            return True

        # Supervisor/Jefe puede ver tickets de sus departamentos,
        # incluso si el ticket ya tiene Owner (para poder revisar tickets de subordinados).
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM miembro_dpto md_sup
                WHERE md_sup.id_operador = %s
                  AND md_sup.rol IN ('Supervisor', 'Jefe')
                  AND md_sup.fecha_desasignacion IS NULL
                  AND (
                        (
                            %s IS NOT NULL
                            AND md_sup.id_depto = %s
                        )
                        OR (
                            %s IS NOT NULL
                            AND EXISTS (
                                SELECT 1
                                FROM miembro_dpto md_owner
                                WHERE md_owner.id_operador = %s
                                  AND md_owner.id_depto = md_sup.id_depto
                                  AND md_owner.fecha_desasignacion IS NULL
                            )
                        )
                        OR (
                            %s IS NOT NULL
                            AND EXISTS (
                                SELECT 1
                                FROM miembro_dpto md_emisor
                                WHERE md_emisor.id_operador = %s
                                  AND md_emisor.id_depto = md_sup.id_depto
                                  AND md_emisor.fecha_desasignacion IS NULL
                            )
                        )
                  )
            """, (
                id_operador,
                info.get('id_depto_ticket'),
                info.get('id_depto_ticket'),
                info.get('id_operador_owner'),
                info.get('id_operador_owner'),
                info.get('id_operador_emisor'),
                info.get('id_operador_emisor'),
            ))
            row = cursor.fetchone()
            sup_count = (row.get('count', 0) if isinstance(row, dict) else row[0]) if row else 0
            if int(sup_count or 0) > 0:
                return True
        except Exception:
            logging.exception('Error verificando permisos de supervisor en operador_puede_ver_ticket')
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        # Si no hay owner, miembros del depto pueden ver (para poder "tomar")
        if not info.get('id_operador_owner') and info.get('id_depto_ticket'):
            conn = None
            cursor = None
            try:
                conn = get_local_db_connection()
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM miembro_dpto
                    WHERE id_operador = %s
                      AND id_depto = %s
                      AND fecha_desasignacion IS NULL
                """, (id_operador, info.get('id_depto_ticket')))
                row = cursor.fetchone()
                return (row.get('count', 0) > 0) if isinstance(row, dict) else (row[0] > 0)
            except Exception:
                logging.exception('Error en TicketModel.operador_puede_ver_ticket')
                return False
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception:
                        pass
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        return False

    @staticmethod
    def operador_puede_escribir_ticket(id_ticket, operador_actual):
        """Valida si el operador puede escribir en el ticket (enviar mensajes)."""
        if TicketModel._is_admin(operador_actual):
            info = TicketModel.get_acl_info(id_ticket)
            return bool(info) and info.get('id_estado') != 4

        id_operador = operador_actual.get('operador_id')
        if not id_operador:
            return False

        info = TicketModel.get_acl_info(id_ticket)
        if not info:
            return False

        # No se escribe en Cerrado
        if info.get('id_estado') == 4:
            return False

        # Emisor puede escribir siempre (mientras no esté cerrado)
        if info.get('id_operador_emisor') and str(info.get('id_operador_emisor')) == str(id_operador):
            return True

        # Debe existir owner y ser el operador actual
        if not info.get('id_operador_owner'):
            return False

        return str(info.get('id_operador_owner')) == str(id_operador)
    
    @staticmethod
    def asignar_ticket(id_ticket, id_operador_nuevo, operador_actual):
        """
        Permite a un supervisor/admin asignar un ticket a otro operador.
        
        Args:
            id_ticket: ID del ticket a asignar
            id_operador_nuevo: ID del operador al que se asigna
            operador_actual: Diccionario con operador_id y rol del que asigna
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            id_operador_asignador = operador_actual.get('operador_id')
            rol_asignador = operador_actual.get('rol', '').lower()
            
            # 1. Verificar permisos: debe ser Admin o Supervisor
            if rol_asignador not in ['admin', 'supervisor']:
                return {'success': False, 'error': 'No tiene permisos para asignar tickets'}
            
            # 2. Verificar que el ticket existe
            cursor.execute("""
                SELECT id_ticket, titulo
                FROM ticket 
                WHERE id_ticket = %s AND deleted_at IS NULL
            """, (id_ticket,))
            
            ticket = cursor.fetchone()
            if not ticket:
                return {'success': False, 'error': 'Ticket no encontrado'}
            
            # 3. Verificar que el operador nuevo existe y está activo
            cursor.execute("""
                SELECT id_operador, nombre
                FROM operador 
                WHERE id_operador = %s AND deleted_at IS NULL
            """, (id_operador_nuevo,))
            
            operador_nuevo = cursor.fetchone()
            if not operador_nuevo:
                return {'success': False, 'error': 'Operador destino no encontrado'}

            # 4. Obtener Owner actual (si existe) antes de desasignar
            cursor.execute("""
                SELECT id_operador
                FROM ticket_operador
                WHERE id_ticket = %s
                  AND rol = 'Owner'
                  AND fecha_desasignacion IS NULL
                LIMIT 1
            """, (id_ticket,))
            owner_anterior = cursor.fetchone()
            id_owner_anterior = owner_anterior.get('id_operador') if owner_anterior else None
            
            # 4. Si ya tiene Owner, desasignarlo primero
            cursor.execute("""
                UPDATE ticket_operador
                SET fecha_desasignacion = NOW()
                WHERE id_ticket = %s 
                  AND rol = 'Owner'
                  AND fecha_desasignacion IS NULL
            """, (id_ticket,))
            
            # 5. Asignar al nuevo operador como Owner
            cursor.execute("""
                INSERT INTO ticket_operador 
                (id_operador, id_ticket, rol, fecha_asignacion)
                VALUES (%s, %s, 'Owner', NOW())
            """, (id_operador_nuevo, id_ticket))
            
            # 6. Registrar en historial
            cursor.execute("""
                INSERT INTO historial_acciones_ticket
                (id_ticket, id_operador, accion, valor_anterior, valor_nuevo, fecha)
                VALUES (%s, %s, 'asignacion', %s, %s, NOW())
            """, (
                id_ticket,
                id_operador_asignador,
                str(id_owner_anterior) if id_owner_anterior is not None else None,
                str(id_operador_nuevo),
            ))

            # 7. Crear notificación para el operador asignado
            try:
                cursor.execute("""
                    INSERT INTO notificacion
                        (id_operador, titulo, mensaje, tipo, entidad_tipo, entidad_id, leido, fecha_creacion)
                    VALUES
                        (%s, %s, %s, 'info', 'ticket', %s, 0, NOW())
                """, (
                    id_operador_nuevo,
                    'Ticket asignado',
                    f'Se te asignó el ticket #{id_ticket}: {ticket["titulo"]}',
                    id_ticket,
                ))
            except Exception:
                # No bloquear la asignación si falla la notificación
                logging.exception('No se pudo crear notificación de asignación')
            
            conn.commit()
            logging.info(f'Ticket {id_ticket} asignado a operador {id_operador_nuevo} por {id_operador_asignador}')
            
            return {
                'success': True,
                'message': f'Ticket asignado a {operador_nuevo["nombre"]}',
                'id_ticket': id_ticket,
                'operador_asignado': operador_nuevo["nombre"]
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.exception(f'Error en asignar_ticket id_ticket={id_ticket}')
            return {'success': False, 'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
