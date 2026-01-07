"""Modelo para gestión de notificaciones."""

from __future__ import annotations

from flask_app.config.conexion_login import execute_query


class NotificacionModel:
    @staticmethod
    def listar_por_operador(
        id_operador: int,
        solo_no_leidas: bool = False,
        limit: int = 20,
        offset: int = 0,
    ):
        where = "WHERE n.id_operador = %s AND n.deleted_at IS NULL"
        params = [id_operador]

        if solo_no_leidas:
            where += " AND n.leido = 0"

        query = f"""
            SELECT
                n.id_notificacion,
                n.id_operador,
                n.titulo,
                n.mensaje,
                n.tipo,
                n.entidad_tipo,
                n.entidad_id,
                n.leido,
                n.fecha_creacion,
                n.fecha_leido
            FROM notificacion n
            {where}
            ORDER BY n.fecha_creacion DESC
            LIMIT %s OFFSET %s
        """
        params.extend([int(limit), int(offset)])

        filas = execute_query(query, tuple(params), fetch_all=True) or []
        total = NotificacionModel.contar_por_operador(id_operador, solo_no_leidas=solo_no_leidas)

        return {
            'success': True,
            'notificaciones': filas,
            'total': total,
        }

    @staticmethod
    def contar_por_operador(id_operador: int, solo_no_leidas: bool = False) -> int:
        where = "WHERE id_operador = %s AND deleted_at IS NULL"
        params = [id_operador]
        if solo_no_leidas:
            where += " AND leido = 0"

        row = execute_query(
            f"SELECT COUNT(*) as total FROM notificacion {where}",
            tuple(params),
            fetch_one=True,
        )
        if not row:
            return 0
        return int(row.get('total', 0)) if isinstance(row, dict) else int(row[0])

    @staticmethod
    def contar_no_leidas(id_operador: int) -> int:
        return NotificacionModel.contar_por_operador(id_operador, solo_no_leidas=True)

    @staticmethod
    def marcar_leida(id_notificacion: int, id_operador: int) -> bool:
        # Restringir por operador para evitar marcar notificaciones ajenas
        query = """
            UPDATE notificacion
            SET leido = 1,
                fecha_leido = NOW()
            WHERE id_notificacion = %s
              AND id_operador = %s
              AND leido = 0
              AND deleted_at IS NULL
        """
        execute_query(query, (id_notificacion, id_operador), commit=True)
        return True

    @staticmethod
    def marcar_todas_leidas(id_operador: int) -> bool:
        query = """
            UPDATE notificacion
            SET leido = 1,
                fecha_leido = NOW()
            WHERE id_operador = %s
              AND leido = 0
              AND deleted_at IS NULL
        """
        execute_query(query, (id_operador,), commit=True)
        return True

    @staticmethod
    def crear_notificacion(
        id_operador: int,
        titulo: str,
        mensaje: str,
        tipo: str = 'info',
        entidad_tipo: str | None = None,
        entidad_id: int | None = None,
    ):
        query = """
            INSERT INTO notificacion
                (id_operador, titulo, mensaje, tipo, entidad_tipo, entidad_id, leido, fecha_creacion)
            VALUES
                (%s, %s, %s, %s, %s, %s, 0, NOW())
        """
        params = (id_operador, titulo, mensaje, tipo, entidad_tipo, entidad_id)
        id_notificacion = execute_query(query, params, commit=True)
        return {'id_notificacion': id_notificacion}
