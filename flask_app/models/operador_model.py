"""
Modelo para gestión de operadores y roles globales
"""
from flask_app.config.conexion_login import execute_query, get_local_db_connection
from flask_app.utils.error_handler import ValidationError
import bcrypt


class OperadorModel:
    """Modelo para operadores del sistema"""
    
    @staticmethod
    def buscar_por_email(email):
        """Busca un operador por email"""
        query = """
            SELECT o.id_operador as id, o.email, o.nombre, o.telefono, 
                   o.estado, o.id_rol_global as rol_id,
                   r.nombre as rol_nombre
            FROM operador o
            LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
            WHERE o.email = %s AND o.deleted_at IS NULL
        """
        return execute_query(query, (email,), fetch_one=True)
    
    @staticmethod
    def buscar_por_id(operador_id):
        """Busca un operador por ID"""
        query = """
            SELECT o.id_operador as id, o.email, o.nombre, o.telefono,
                   o.estado, o.id_rol_global as rol_id,
                   r.nombre as rol_nombre
            FROM operador o
            LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
            WHERE o.id_operador = %s AND o.deleted_at IS NULL
        """
        return execute_query(query, (operador_id,), fetch_one=True)
    
    @staticmethod
    def listar_todos():
        """Lista todos los operadores activos con sus departamentos"""
        conn = None
        cursor = None
        try:
            from flask_app.config.conexion_login import get_local_db_connection
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Obtener operadores
            query = """
                SELECT o.id_operador, o.email, o.nombre, o.telefono,
                       o.estado, o.id_rol_global as rol_id,
                       r.nombre as rol_nombre
                FROM operador o
                LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
                WHERE o.deleted_at IS NULL
                ORDER BY o.nombre
            """
            cursor.execute(query)
            operadores = cursor.fetchall()
            
            # Para cada operador, obtener sus departamentos
            operadores_con_deptos = []
            for op in operadores:
                operador_dict = dict(op) if isinstance(op, dict) else {
                    'id_operador': op[0],
                    'email': op[1],
                    'nombre': op[2],
                    'telefono': op[3],
                    'estado': op[4],
                    'rol_id': op[5],
                    'rol_nombre': op[6]
                }
                
                # Obtener departamentos del operador
                cursor.execute("""
                    SELECT md.id_depto, d.descripcion as departamento_nombre,
                           md.rol as rol_departamento
                    FROM miembro_dpto md
                    INNER JOIN departamento d ON md.id_depto = d.id_depto
                    WHERE md.id_operador = %s 
                      AND md.fecha_desasignacion IS NULL
                """, (operador_dict['id_operador'],))
                
                departamentos = cursor.fetchall()
                operador_dict['departamentos'] = [
                    {
                        'id_depto': d['id_depto'] if isinstance(d, dict) else d[0],
                        'id_departamento': d['id_depto'] if isinstance(d, dict) else d[0],
                        'nombre': d['departamento_nombre'] if isinstance(d, dict) else d[1],
                        'rol': d['rol_departamento'] if isinstance(d, dict) else d[2]
                    }
                    for d in departamentos
                ]
                
                operadores_con_deptos.append(operador_dict)
            
            cursor.close()
            conn.close()
            return operadores_con_deptos
            
        except Exception as e:
            import logging
            logging.error(f"Error en listar_todos: {e}")
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            # Fallback al query simple
            query = """
                SELECT o.id_operador, o.email, o.nombre, o.telefono,
                       o.estado, o.id_rol_global as rol_id,
                       r.nombre as rol_nombre
                FROM operador o
                LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
                WHERE o.deleted_at IS NULL
                ORDER BY o.nombre
            """
            return execute_query(query, fetch_all=True)
    
    @staticmethod
    def listar_por_departamento(id_depto):
        """Lista operadores de un departamento específico"""
        query = """
            SELECT DISTINCT o.id_operador, o.email, o.nombre, o.telefono,
                   o.estado, o.id_rol_global as rol_id,
                   r.nombre as rol_nombre,
                   md.id_depto,
                   md.rol as rol_departamento
            FROM operador o
            LEFT JOIN rol_global r ON o.id_rol_global = r.id_rol
            INNER JOIN miembro_dpto md ON o.id_operador = md.id_operador
            WHERE o.deleted_at IS NULL 
              AND md.id_depto = %s 
              AND md.fecha_desasignacion IS NULL
            ORDER BY o.nombre
        """
        return execute_query(query, (id_depto,), fetch_all=True)
    
    @staticmethod
    def obtener_departamentos_operador(id_operador):
        """Obtiene los departamentos y roles de un operador"""
        query = """
            SELECT md.id_depto, d.descripcion as departamento_nombre,
                   md.rol as rol_departamento, md.fecha_asignacion
            FROM miembro_dpto md
            INNER JOIN departamento d ON md.id_depto = d.id_depto
            WHERE md.id_operador = %s 
              AND md.fecha_desasignacion IS NULL
            ORDER BY d.descripcion
        """
        return execute_query(query, (id_operador,), fetch_all=True)
    
    @staticmethod
    def obtener_perfil_completo(id_operador):
        """Obtiene el perfil completo del operador con sus departamentos y roles"""
        operador = OperadorModel.buscar_por_id(id_operador)
        if not operador:
            return None
        
        departamentos = OperadorModel.obtener_departamentos_operador(id_operador)
        
        # Determinar si es supervisor/jefe en algún departamento
        es_supervisor = any(d.get('rol_departamento') in ('Supervisor', 'Jefe') for d in departamentos) if departamentos else False
        
        return {
            'id': operador['id'],
            'nombre': operador['nombre'],
            'email': operador['email'],
            'telefono': operador.get('telefono'),
            'estado': operador.get('estado'),
            'rol_global': operador.get('rol_nombre'),
            'departamentos': departamentos or [],
            'es_supervisor': es_supervisor,
            'es_admin': operador.get('rol_nombre') == 'Admin'
        }

    @staticmethod
    def crear(data, password):
        """Crea un operador en la BD local y su credencial en la BD externa (adrecrear_usuarios)."""
        email = (data.get('email') or '').strip().lower()
        nombre = (data.get('nombre') or '').strip()
        telefono = (data.get('telefono') or None)
        club_us = data.get('club_us')

        try:
            id_rol_global = int(data.get('id_rol_global'))
        except (TypeError, ValueError):
            raise ValidationError('id_rol_global inválido')

        if not email:
            raise ValidationError('Email requerido')
        if not nombre:
            raise ValidationError('Nombre requerido')
        if not password:
            raise ValidationError('Contraseña requerida')

        # Validar duplicado en BD local
        existente_local = execute_query(
            "SELECT id_operador FROM operador WHERE email = %s AND deleted_at IS NULL",
            (email,),
            fetch_one=True
        )
        if existente_local:
            raise ValidationError('Ya existe un usuario con ese email en el sistema')

        # Conexiones manuales para transacción dual
        from flask_app.config.conexion_login import get_db_connection

        local_conn = None
        local_cursor = None
        ext_conn = None
        ext_cursor = None

        try:
            local_conn = get_local_db_connection()
            local_cursor = local_conn.cursor()

            ext_conn = get_db_connection()
            ext_cursor = ext_conn.cursor()

            # Validar duplicado en BD externa (si ya existe, no creamos el operador local)
            ext_cursor.execute(
                "SELECT email_usuario FROM adrecrear_usuarios WHERE email_usuario = %s",
                (email,)
            )
            if ext_cursor.fetchone():
                raise ValidationError('Ya existe un usuario con ese email en el sistema de autenticación')

            # 1) Insert local
            local_cursor.execute(
                """
                INSERT INTO operador (email, nombre, telefono, estado, id_rol_global)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (email, nombre, telefono, 1, id_rol_global)
            )
            operador_id = local_cursor.lastrowid

            # 2) Insert externo (bcrypt)
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

            ext_cursor.execute(
                """
                INSERT INTO adrecrear_usuarios (email_usuario, nombre_usuario, telefono, clave_usuario, estado_usuario, club_us)
                VALUES (%s, %s, %s, %s, 1, %s)
                """,
                (email, nombre, telefono, hashed_password, club_us)
            )

            # Commit ambos
            ext_conn.commit()
            local_conn.commit()

            return operador_id

        except ValidationError:
            if local_conn:
                local_conn.rollback()
            if ext_conn:
                ext_conn.rollback()
            raise
        except Exception as e:
            if local_conn:
                local_conn.rollback()
            if ext_conn:
                ext_conn.rollback()
            raise e
        finally:
            if local_cursor:
                local_cursor.close()
            if local_conn:
                local_conn.close()
            if ext_cursor:
                ext_cursor.close()
            if ext_conn:
                ext_conn.close()

    @staticmethod
    def actualizar_admin(operador_id, data):
        """Actualiza un operador en BD local y replica cambios en BD externa adrecrear_usuarios."""
        operador_actual = OperadorModel.buscar_por_id(operador_id)
        if not operador_actual:
            raise ValidationError('Operador no encontrado')

        nuevo_email = (data.get('email') or '').strip().lower()
        nuevo_nombre = (data.get('nombre') or '').strip()
        nuevo_telefono = data.get('telefono')

        try:
            nuevo_estado = int(data.get('estado'))
        except (TypeError, ValueError):
            raise ValidationError('estado inválido')

        try:
            nuevo_rol_id = int(data.get('id_rol_global'))
        except (TypeError, ValueError):
            raise ValidationError('id_rol_global inválido')

        if not nuevo_email:
            raise ValidationError('Email requerido')
        if not nuevo_nombre:
            raise ValidationError('Nombre requerido')

        email_anterior = (operador_actual.get('email') or '').strip().lower()

        # Validar duplicado en BD local (si cambia el email)
        if nuevo_email != email_anterior:
            existente_local = execute_query(
                "SELECT id_operador FROM operador WHERE email = %s AND deleted_at IS NULL",
                (nuevo_email,),
                fetch_one=True
            )
            if existente_local:
                raise ValidationError('Ya existe un usuario con ese email en el sistema')

        from flask_app.config.conexion_login import get_db_connection

        local_conn = None
        local_cursor = None
        ext_conn = None
        ext_cursor = None

        try:
            local_conn = get_local_db_connection()
            local_cursor = local_conn.cursor()

            ext_conn = get_db_connection()
            ext_cursor = ext_conn.cursor()

            # Validar duplicado en BD externa (si cambia email)
            if nuevo_email != email_anterior:
                ext_cursor.execute(
                    "SELECT email_usuario FROM adrecrear_usuarios WHERE email_usuario = %s",
                    (nuevo_email,)
                )
                if ext_cursor.fetchone():
                    raise ValidationError('Ya existe un usuario con ese email en el sistema de autenticación')

            # Update local
            local_cursor.execute(
                """
                UPDATE operador
                SET email = %s,
                    nombre = %s,
                    telefono = %s,
                    estado = %s,
                    id_rol_global = %s
                WHERE id_operador = %s AND deleted_at IS NULL
                """,
                (nuevo_email, nuevo_nombre, nuevo_telefono, nuevo_estado, nuevo_rol_id, operador_id)
            )

            # Update externa (por email anterior)
            ext_cursor.execute(
                """
                UPDATE adrecrear_usuarios
                SET email_usuario = %s,
                    nombre_usuario = %s,
                    telefono = %s,
                    estado_usuario = %s
                WHERE email_usuario = %s
                """,
                (nuevo_email, nuevo_nombre, nuevo_telefono, 1 if nuevo_estado == 1 else 0, email_anterior)
            )

            # Commit ambos
            ext_conn.commit()
            local_conn.commit()

            return True

        except ValidationError:
            if local_conn:
                local_conn.rollback()
            if ext_conn:
                ext_conn.rollback()
            raise
        except Exception as e:
            if local_conn:
                local_conn.rollback()
            if ext_conn:
                ext_conn.rollback()
            raise e
        finally:
            if local_cursor:
                local_cursor.close()
            if local_conn:
                local_conn.close()
            if ext_cursor:
                ext_cursor.close()
            if ext_conn:
                ext_conn.close()


class RolGlobalModel:
    """Modelo para roles globales"""
    
    @staticmethod
    def listar_activos():
        """Lista todos los roles activos"""
        query = """
            SELECT id_rol as id, nombre, activo
            FROM rol_global
            WHERE activo = 1
            ORDER BY nombre
        """
        return execute_query(query, fetch_all=True)
    
    @staticmethod
    def buscar_por_id(rol_id):
        """Busca un rol por ID"""
        query = """
            SELECT id_rol as id, nombre, activo
            FROM rol_global
            WHERE id_rol = %s
        """
        return execute_query(query, (rol_id,), fetch_one=True)
