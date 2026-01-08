"""Modelos para gestión de permisos y asignación de permisos a roles globales."""

from __future__ import annotations

from typing import Iterable

from flask_app.config.conexion_login import execute_query, get_local_db_connection
from flask_app.utils.error_handler import ValidationError


class PermisoModel:
    @staticmethod
    def listar_activos():
        query = """
            SELECT id_permiso as id, codigo, descripcion, activo
            FROM permiso
            WHERE activo = 1
            ORDER BY codigo
        """
        return execute_query(query, fetch_all=True)


class RolPermisoModel:
    @staticmethod
    def listar_roles_con_permisos(solo_activos: bool = True):
        where = "WHERE r.activo = 1" if solo_activos else ""

        # Retorna una fila por (rol, permiso). Luego se agrupa en Python.
        query = f"""
            SELECT r.id_rol as rol_id, r.nombre as rol_nombre, r.activo as rol_activo,
                   p.id_permiso as permiso_id, p.codigo as permiso_codigo, p.descripcion as permiso_descripcion
            FROM rol_global r
            LEFT JOIN rol_permiso rp ON rp.id_rol = r.id_rol
            LEFT JOIN permiso p ON p.id_permiso = rp.id_permiso
            {where}
            ORDER BY r.nombre, p.codigo
        """

        rows = execute_query(query, fetch_all=True) or []

        roles: dict[int, dict] = {}
        for row in rows:
            rol_id = row.get('rol_id')
            if rol_id is None:
                continue

            if rol_id not in roles:
                roles[rol_id] = {
                    'id': rol_id,
                    'nombre': row.get('rol_nombre'),
                    'activo': row.get('rol_activo'),
                    'permisos': []
                }

            permiso_id = row.get('permiso_id')
            if permiso_id:
                roles[rol_id]['permisos'].append({
                    'id': permiso_id,
                    'codigo': row.get('permiso_codigo'),
                    'descripcion': row.get('permiso_descripcion')
                })

        return list(roles.values())

    @staticmethod
    def obtener_permiso_ids_por_rol(rol_id: int):
        query = """
            SELECT id_permiso
            FROM rol_permiso
            WHERE id_rol = %s
        """
        rows = execute_query(query, (rol_id,), fetch_all=True) or []
        return [r['id_permiso'] for r in rows if r.get('id_permiso') is not None]

    @staticmethod
    def reemplazar_permisos(rol_id: int, permiso_ids: Iterable[int]):
        try:
            rol_id = int(rol_id)
        except (TypeError, ValueError):
            raise ValidationError('rol_id inválido')

        permiso_ids_limpios: list[int] = []
        seen = set()
        for pid in permiso_ids or []:
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                raise ValidationError('permiso_ids contiene valores inválidos')
            if pid_int in seen:
                continue
            seen.add(pid_int)
            permiso_ids_limpios.append(pid_int)

        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM rol_permiso WHERE id_rol = %s", (rol_id,))

            if permiso_ids_limpios:
                cursor.executemany(
                    "INSERT INTO rol_permiso (id_rol, id_permiso) VALUES (%s, %s)",
                    [(rol_id, pid) for pid in permiso_ids_limpios]
                )

            conn.commit()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class RolGlobalAdminModel:
    """Operaciones administrativas sobre rol_global (crear)."""

    @staticmethod
    def crear(nombre: str, activo: int = 1) -> int:
        nombre = (nombre or '').strip()
        if not nombre:
            raise ValidationError('nombre requerido')

        try:
            activo = int(activo)
        except (TypeError, ValueError):
            activo = 1

        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()

            # Evitar duplicados por nombre
            cursor.execute("SELECT id_rol FROM rol_global WHERE nombre = %s", (nombre,))
            existente = cursor.fetchone()
            if existente:
                raise ValidationError('Ya existe un rol con ese nombre')

            cursor.execute(
                "INSERT INTO rol_global (nombre, activo) VALUES (%s, %s)",
                (nombre, activo)
            )
            conn.commit()
            return int(cursor.lastrowid)
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
    def actualizar(rol_id: int, nombre: str | None = None, activo: int | None = None) -> bool:
        try:
            rol_id = int(rol_id)
        except (TypeError, ValueError):
            raise ValidationError('rol_id inválido')

        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id_rol, nombre, activo FROM rol_global WHERE id_rol = %s", (rol_id,))
            actual = cursor.fetchone()
            if not actual:
                raise ValidationError('Rol no encontrado')

            nombre_actual = actual['nombre'] if isinstance(actual, dict) else actual[1]
            activo_actual = actual['activo'] if isinstance(actual, dict) else actual[2]

            # Proteger roles base para no romper autorización/UX existente
            roles_base = {'Admin', 'Supervisor', 'Agente'}
            if nombre_actual in roles_base:
                if nombre is not None and (nombre or '').strip() != nombre_actual:
                    raise ValidationError('No se puede renombrar un rol base del sistema')
                if activo is not None and int(activo) != int(activo_actual) and nombre_actual == 'Admin':
                    raise ValidationError('No se puede desactivar el rol Admin')

            updates = []
            params = []

            if nombre is not None:
                nombre = (nombre or '').strip()
                if not nombre:
                    raise ValidationError('nombre requerido')

                cursor.execute(
                    "SELECT id_rol FROM rol_global WHERE nombre = %s AND id_rol <> %s",
                    (nombre, rol_id)
                )
                dup = cursor.fetchone()
                if dup:
                    raise ValidationError('Ya existe un rol con ese nombre')

                updates.append('nombre = %s')
                params.append(nombre)

            if activo is not None:
                try:
                    activo_int = int(activo)
                except (TypeError, ValueError):
                    raise ValidationError('activo inválido')
                if activo_int not in (0, 1):
                    raise ValidationError('activo inválido')
                updates.append('activo = %s')
                params.append(activo_int)

            if not updates:
                return True

            params.append(rol_id)
            cursor.execute(
                f"UPDATE rol_global SET {', '.join(updates)} WHERE id_rol = %s",
                tuple(params)
            )
            conn.commit()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
