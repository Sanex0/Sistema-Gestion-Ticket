"""Modelo para consultar el historial/auditoría de acciones.

Este proyecto ya cuenta con la tabla `historial_acciones_ticket`, la cual registra
acciones principalmente asociadas a tickets (y algunas acciones de mensajes).

Nota: si se requiere auditar acciones NO asociadas a tickets (ej: cambios de roles,
login, cambios de departamentos), se necesita una tabla adicional o extender el
esquema existente para permitir registros sin `id_ticket`.
"""

from __future__ import annotations

from flask_app.config.conexion_login import execute_query
from datetime import datetime


class AuditoriaModel:
    @staticmethod
    def registrar(evento: dict):
        """No-op.

        El historial se registra en `historial_acciones_ticket` desde Ticket/Mensaje.
        """
        return True

    @staticmethod
    def obtener_depto_principal_operador(id_operador: int):
        query = """
            SELECT md.id_depto
            FROM miembro_dpto md
            WHERE md.id_operador = %s
              AND md.fecha_desasignacion IS NULL
            ORDER BY md.fecha_asignacion DESC
            LIMIT 1
        """
        row = execute_query(query, (id_operador,), fetch_one=True)
        if not row:
            return None
        return row.get('id_depto')

    @staticmethod
    def listar(depto_id=None, operador_id=None, accion=None, fecha=None, limit=50, offset=0):
        """Lista historial de acciones filtrando por depto/operador/accion/fecha (YYYY-MM-DD).

        Depende de que `ticket.id_depto` exista (ver script `agregar_campo_depto_ticket.py`).
        """
        where = []
        params = []

        accion_norm = str(accion).strip().lower() if accion is not None else None

        if depto_id:
            # Por defecto filtramos por depto destino del ticket.
            # Excepción solicitada: para "Ticket creado" permitir ver el evento también
            # desde el depto del operador creador (depto origen).
            if accion_norm == 'ticket creado':
                where.append(
                    "(" 
                    "t.id_depto = %s OR "
                    "EXISTS (" 
                    "  SELECT 1 FROM miembro_dpto md "
                    "  WHERE md.id_operador = h.id_operador "
                    "    AND md.fecha_desasignacion IS NULL "
                    "    AND md.id_depto = %s" 
                    ")" 
                    ")"
                )
                params.append(int(depto_id))
                params.append(int(depto_id))
            else:
                where.append('t.id_depto = %s')
                params.append(int(depto_id))

        if operador_id:
            where.append('h.id_operador = %s')
            params.append(int(operador_id))

        if accion and accion != 'all':
            # Algunas tablas pueden tener collation case-sensitive; normalizar para evitar
            # que 'Ticket Creado' != 'Ticket creado' rompa el filtrado.
            where.append('LOWER(TRIM(h.accion)) = LOWER(TRIM(%s))')
            params.append(str(accion))

        if fecha:
            # fecha: 'YYYY-MM-DD'
            where.append('DATE(h.fecha) = %s')
            params.append(str(fecha))

        where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

        query = f"""
            SELECT h.id_historial_ticket as id,
                   h.fecha,
                   h.id_operador,
                   h.id_usuarioext,
                   o.nombre as operador_nombre,
                   t.id_depto,
                   d.descripcion as depto_nombre,
                   h.accion,
                   h.id_ticket,
                   h.valor_anterior,
                   h.valor_nuevo
            FROM historial_acciones_ticket h
            INNER JOIN ticket t ON h.id_ticket = t.id_ticket
            LEFT JOIN departamento d ON t.id_depto = d.id_depto
            LEFT JOIN operador o ON h.id_operador = o.id_operador
            {where_sql}
            ORDER BY h.fecha DESC
            LIMIT %s OFFSET %s
        """

        params.extend([int(limit), int(offset)])
        rows = execute_query(query, tuple(params), fetch_all=True) or []

        # Normalizar salida al formato que consume el frontend de auditoría
        out = []
        for r in rows:
            fecha_raw = r.get('fecha')
            if isinstance(fecha_raw, datetime):
                fecha_out = fecha_raw.strftime('%Y-%m-%d %H:%M:%S')
            elif fecha_raw is None:
                fecha_out = None
            else:
                fecha_out = str(fecha_raw)

            # detalle: cambios
            detalle = None
            va = r.get('valor_anterior')
            vn = r.get('valor_nuevo')
            if va is not None or vn is not None:
                detalle = f"{va or ''} -> {vn or ''}".strip()

            out.append({
                'id': r.get('id'),
                'fecha': fecha_out,
                'id_operador': r.get('id_operador'),
                'id_usuarioext': r.get('id_usuarioext'),
                'operador_nombre': r.get('operador_nombre') or 'Operador',
                'id_depto': r.get('id_depto'),
                'depto_nombre': r.get('depto_nombre'),
                'accion': r.get('accion'),
                'id_ticket': r.get('id_ticket'),
                'valor_anterior': r.get('valor_anterior'),
                'valor_nuevo': r.get('valor_nuevo'),
                'metodo': None,
                'endpoint': f"Ticket #{r.get('id_ticket')}" if r.get('id_ticket') else None,
                'status_code': None,
                'ip': None,
                'detalle': detalle
            })

        return out

    @staticmethod
    def listar_acciones_distintas(depto_id=None, operador_id=None):
        """Lista acciones distintas disponibles según filtros.

        - Si hay depto_id: devuelve acciones visibles para ese depto.
          Incluye el caso especial de "Ticket creado" por depto del operador creador.
        - Si hay operador_id sin depto_id: devuelve acciones del operador en todos los deptos.
        """
        where = [
            "h.accion IS NOT NULL",
            "TRIM(h.accion) <> ''",
        ]
        params = []

        if depto_id:
            where.append(
                "("
                " t.id_depto = %s "
                " OR (LOWER(TRIM(h.accion)) = 'ticket creado' AND EXISTS ("
                "     SELECT 1 FROM miembro_dpto md"
                "     WHERE md.id_operador = h.id_operador"
                "       AND md.fecha_desasignacion IS NULL"
                "       AND md.id_depto = %s"
                " ))"
                ")"
            )
            params.append(int(depto_id))
            params.append(int(depto_id))

        if operador_id:
            where.append('h.id_operador = %s')
            params.append(int(operador_id))

        where_sql = 'WHERE ' + ' AND '.join(where)

        query = f"""
            SELECT MIN(h.accion) AS accion
            FROM historial_acciones_ticket h
            INNER JOIN ticket t ON h.id_ticket = t.id_ticket
            {where_sql}
            GROUP BY LOWER(TRIM(h.accion))
            ORDER BY MIN(h.accion)
        """

        rows = execute_query(query.strip(), tuple(params), fetch_all=True) or []
        return [r.get('accion') for r in rows if r.get('accion')]
