from flask_app.config.conexion_login import execute_query, get_local_db_connection
from datetime import datetime


class MensajeModel:
    """
    Modelo para gestionar mensajes de tickets.
    Implementación conservadora de crear_desde_email para reintegración segura.
    """

    @staticmethod
    def crear_mensaje(data):
        from flask_app.config.conexion_login import get_local_db_connection
        import pymysql.cursors

        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            query = """
                INSERT INTO mensaje 
                (tipo_mensaje, asunto, contenido, remitente_id, remitente_tipo, 
                 estado_mensaje, id_ticket, id_canal)
                VALUES (%s, %s, %s, %s, %s, 'Normal', %s, %s)
            """

            params = (
                data.get('tipo_mensaje', 'Publico'),
                data.get('asunto', ''),
                data.get('contenido', ''),
                data.get('remitente_id'),
                data.get('remitente_tipo'),
                data.get('id_ticket'),
                data.get('id_canal', 1),
            )

            cursor.execute(query, params)
            id_msg = cursor.lastrowid

            remitente_tipo = data.get('remitente_tipo')
            tipo_mensaje = data.get('tipo_mensaje', 'Publico')

            if remitente_tipo == 'Operador':
                cursor.execute(
                    """
                    INSERT INTO historial_acciones_ticket 
                    (id_ticket, id_operador, accion, valor_nuevo)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (data['id_ticket'], data['remitente_id'], f"Mensaje {tipo_mensaje.lower()}", data.get('asunto')),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO historial_acciones_ticket 
                    (id_ticket, id_usuarioext, accion, valor_nuevo)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (data['id_ticket'], data.get('remitente_id'), f"Mensaje {tipo_mensaje.lower()}", data.get('asunto')),
                )

            conn.commit()

            # Enviar email al usuario si corresponde
            try:
                if remitente_tipo == 'Operador' and tipo_mensaje.lower() == 'publico':
                    cursor.execute(
                        "SELECT t.id_ticket, t.titulo, t.id_usuarioext, ue.email as usuario_email FROM ticket t LEFT JOIN usuario_ext ue ON t.id_usuarioext = ue.id_usuario WHERE t.id_ticket = %s",
                        (data['id_ticket'],),
                    )
                    trow = cursor.fetchone() or {}
                    usuario_email = trow.get('usuario_email') if isinstance(trow, dict) else None
                    if usuario_email:
                        try:
                            from flask_app.services.email_outbound import send_email
                            ticket_title = trow.get('titulo') if isinstance(trow, dict) else ''
                            subj = f"Ticket #{data['id_ticket']}: ({ticket_title or data.get('asunto','')})"
                            body = (data.get('contenido') or '') + "\n\nRespuesta enviada por el equipo de soporte."
                            try:
                                send_email(usuario_email, subj, body, id_msg=id_msg, id_ticket=data['id_ticket'])
                            except Exception:
                                pass
                        except Exception:
                            pass
            except Exception:
                pass

            return {'id_msg': id_msg}

        except Exception:
            if conn:
                conn.rollback()
            raise
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

        if not incluir_privados or tipo_usuario == 'Usuario':
            query += " AND m.tipo_mensaje = 'Publico'"

        query += " ORDER BY m.fecha_envio ASC"

        return execute_query(query, (id_ticket,), fetch_all=True)

    @staticmethod
    def actualizar_mensaje(id_msg, data):
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
            id_msg,
        )

        return execute_query(query, params, commit=True)

    @staticmethod
    def eliminar_mensaje(id_msg, soft_delete=True):
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
        query = """
            UPDATE mensaje 
            SET tipo_mensaje = 'Privado'
            WHERE id_msg = %s AND deleted_at IS NULL
        """

        return execute_query(query, (id_msg,), commit=True)

    @staticmethod
    def crear_desde_email(email_data):
        """
        Versión conservadora de creación/adjunto desde email.
        - Busca usuario por email
        - Trata de mapear In-Reply-To a ticket por `email_message_ids`
        - Si no hay ticket, crea uno básico y adjunta primer mensaje
        - Persiste `email_message_ids` si viene `message_id`
        """
        import pymysql.cursors
        import logging
        from flask_app.models.usuario_ext_model import UsuarioExtModel

        conn = get_local_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            usuario_id = None
            from_email = email_data.get('from_email')
            if from_email:
                row = UsuarioExtModel.buscar_por_email(from_email)
                if row:
                    usuario_id = row.get('id') if isinstance(row, dict) else row[0]
                else:
                    try:
                        usuario_id = UsuarioExtModel.crear_usuario({
                            'rut': None,
                            'nombre': email_data.get('from_name') or from_email.split('@')[0],
                            'telefono': None,
                            'email': from_email,
                            'existe_flex': 0,
                        })
                    except Exception:
                        logging.exception('No se pudo crear usuario_ext desde email')

            if not usuario_id:
                raise ValueError('No se pudo determinar usuario_ext para el remitente')

            message_id = email_data.get('message_id')
            message_id_norm = None
            if message_id:
                try:
                    message_id_norm = str(message_id).strip().lower()[:250]
                except Exception:
                    message_id_norm = None

            def _store_message_id(id_ticket_val, id_msg_val=None):
                if not message_id_norm or not id_ticket_val:
                    return
                try:
                    raw_headers_trunc = (email_data.get('raw_headers') or '')[:2000]
                    execute_query(
                        "INSERT IGNORE INTO email_message_ids (message_id, id_msg, id_ticket, in_reply_to, raw_headers) VALUES (%s,%s,%s,%s,%s)",
                        (message_id_norm, id_msg_val, id_ticket_val, email_data.get('in_reply_to'), raw_headers_trunc),
                        commit=True,
                    )
                except Exception:
                    logging.exception('No se pudo insertar email_message_ids')

            ticket_id = None
            in_reply_to = email_data.get('in_reply_to')
            if in_reply_to:
                try:
                    ref = execute_query("SELECT id_ticket FROM email_message_ids WHERE message_id = %s", (in_reply_to,), fetch_one=True)
                    if ref:
                        ticket_id = ref.get('id_ticket') if isinstance(ref, dict) else ref[0]
                except Exception:
                    logging.exception('Error buscando In-Reply-To')

            # Si es reply a un ticket, validar reglas de negocio
            if ticket_id:
                # Si el ticket está cerrado, ignorar mensajes
                try:
                    row = execute_query("SELECT id_estado FROM ticket WHERE id_ticket = %s", (ticket_id,), fetch_one=True)
                    estado_actual = row.get('id_estado') if isinstance(row, dict) else row[0]
                    if estado_actual == 4:
                        _store_message_id(ticket_id)
                        return {'success': True, 'skipped': True, 'reason': 'ticket_closed', 'id_ticket': ticket_id, 'created_ticket': False}
                except Exception:
                    logging.exception('Error leyendo estado de ticket')

                # Si el ticket no está tomado por un operador, ignorar respuesta
                try:
                    taken = execute_query(
                        "SELECT COUNT(*) as total FROM ticket_operador WHERE id_ticket = %s AND rol = 'Owner' AND fecha_desasignacion IS NULL",
                        (ticket_id,),
                        fetch_one=True,
                    )
                    total_taken = taken.get('total') if isinstance(taken, dict) else taken[0]
                    if int(total_taken or 0) == 0:
                        _store_message_id(ticket_id)
                        return {'success': True, 'skipped': True, 'reason': 'ticket_not_taken', 'id_ticket': ticket_id, 'created_ticket': False}
                except Exception:
                    logging.exception('Error validando ticket tomado')

                # Comando de cierre por correo
                body_text = (email_data.get('body') or '').strip()
                if body_text.upper() == 'CERRAR':
                    try:
                        cursor.execute("UPDATE ticket SET id_estado = 4, fecha_resolucion = NOW() WHERE id_ticket = %s", (ticket_id,))
                        cursor.execute(
                            "INSERT INTO historial_acciones_ticket (id_ticket, id_usuarioext, accion, valor_nuevo, fecha) VALUES (%s,%s,'Ticket cerrado',%s,NOW())",
                            (ticket_id, usuario_id, 'CERRAR'),
                        )
                        conn.commit()
                        _store_message_id(ticket_id)
                        return {'success': True, 'skipped': True, 'reason': 'ticket_closed_by_user', 'id_ticket': ticket_id, 'created_ticket': False}
                    except Exception:
                        logging.exception('Error cerrando ticket por correo')

            id_msg = None

            if ticket_id:
                cursor.execute(
                    """
                    INSERT INTO mensaje (tipo_mensaje, asunto, contenido, remitente_id, remitente_tipo, estado_mensaje, fecha_envio, id_ticket, id_canal)
                    VALUES (%s,%s,%s,%s,%s,%s,NOW(),%s,%s)
                    """,
                    (
                        'Publico',
                        (email_data.get('subject') or '')[:50],
                        (email_data.get('body') or '')[:500],
                        int(usuario_id) if usuario_id else None,
                        'Usuario',
                        'Normal',
                        ticket_id,
                        int(email_data.get('id_canal', 1)),
                    ),
                )
                id_msg = cursor.lastrowid
                try:
                    cursor.execute(
                        "INSERT INTO historial_acciones_ticket (id_ticket, id_usuarioext, accion, valor_nuevo, fecha) VALUES (%s,%s,'Mensaje publico',%s,NOW())",
                        (ticket_id, usuario_id, (email_data.get('subject') or '')[:100]),
                    )
                except Exception:
                    logging.exception('No se pudo registrar historial (append)')
                conn.commit()
                _store_message_id(ticket_id, id_msg)
                return {'id_msg': id_msg, 'id_ticket': ticket_id, 'created_ticket': False}
            else:
                # Regla: un usuario solo puede tener 1 ticket abierto
                try:
                    row = execute_query(
                        "SELECT id_ticket FROM ticket WHERE id_usuarioext = %s AND id_estado != 4 ORDER BY fecha_ini DESC LIMIT 1",
                        (usuario_id,),
                        fetch_one=True,
                    )
                    if row:
                        existing_ticket = row.get('id_ticket') if isinstance(row, dict) else row[0]
                        _store_message_id(existing_ticket)
                        return {'success': True, 'skipped': True, 'reason': 'open_ticket_exists', 'id_ticket': existing_ticket, 'created_ticket': False}
                except Exception:
                    logging.exception('Error verificando ticket abierto existente')

                # defaults and defensive parsing for numeric fields
                try:
                    id_depto_val = int(email_data.get('id_depto')) if email_data.get('id_depto') not in (None, '') else 1
                except Exception:
                    id_depto_val = 1

                try:
                    id_canal_val = int(email_data.get('id_canal', 1))
                except Exception:
                    id_canal_val = 1

                cursor.execute(
                    """
                    INSERT INTO ticket (titulo, tipo_ticket, descripcion, fecha_ini, id_estado, id_prioridad, id_usuarioext, id_club, id_sla, id_canal, id_depto)
                    VALUES (%s,%s,%s,NOW(),%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        (email_data.get('subject') or '')[:200],
                        'Publico',
                        (email_data.get('body') or '')[:1000],
                        1,
                        3,
                        usuario_id,
                        1,
                        1,
                        id_canal_val,
                        id_depto_val,
                    ),
                )
                ticket_id = cursor.lastrowid
                try:
                    cursor.execute(
                        "INSERT INTO historial_acciones_ticket (id_ticket, id_usuarioext, accion, valor_nuevo, fecha) VALUES (%s,%s,'Ticket creado',%s,NOW())",
                        (ticket_id, usuario_id, (email_data.get('subject') or '')[:200]),
                    )
                except Exception:
                    logging.exception('No se pudo registrar historial (ticket creado)')

                cursor.execute(
                    "INSERT INTO mensaje (tipo_mensaje, asunto, contenido, remitente_id, remitente_tipo, estado_mensaje, fecha_envio, id_ticket, id_canal) VALUES (%s,%s,%s,%s,%s,%s,NOW(),%s,%s)",
                    (
                        'Publico',
                        (email_data.get('subject') or '')[:50],
                        (email_data.get('body') or '')[:500],
                        int(usuario_id) if usuario_id else None,
                        'Usuario',
                        'Normal',
                        ticket_id,
                        id_canal_val,
                    ),
                )
                id_msg = cursor.lastrowid
                try:
                    cursor.execute(
                        "INSERT INTO historial_acciones_ticket (id_ticket, id_usuarioext, accion, valor_nuevo, fecha) VALUES (%s,%s,'Mensaje publico',%s,NOW())",
                        (ticket_id, usuario_id, (email_data.get('subject') or '')[:100]),
                    )
                except Exception:
                    logging.exception('No se pudo registrar historial (mensaje inicial)')
                conn.commit()
                _store_message_id(ticket_id, id_msg)

            return {'id_msg': id_msg, 'id_ticket': ticket_id, 'created_ticket': True}
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
