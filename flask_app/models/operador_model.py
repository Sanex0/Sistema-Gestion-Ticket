"""
Modelo para gestión de operadores y roles globales
"""
from flask_app.config.conexion_login import execute_query, get_local_db_connection


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
