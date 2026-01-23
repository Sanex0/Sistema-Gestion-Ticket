import pymysql
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """
    Conexión ORIGINAL para login (base de datos EXTERNA).
    Mantiene compatibilidad con el código existente.
    """
    # Prefer environment variables. DO NOT store production secrets in source.
    # In production set these environment variables on the server (or use a secrets manager).
    DB_HOST = os.getenv('EXTERNAL_DB_HOST', '127.0.0.1')
    DB_PORT = int(os.getenv('EXTERNAL_DB_PORT', 3306))
    DB_USER = os.getenv('EXTERNAL_DB_USER', 'root')
    DB_PASS = os.getenv('EXTERNAL_DB_PASSWORD', '')
    DB_NAME = os.getenv('EXTERNAL_DB_NAME', 'sistemas')

    # Optional SSL/TLS for external DB: provide path to CA file in EXTERNAL_DB_SSL_CA
    ssl_ca = os.getenv('EXTERNAL_DB_SSL_CA') or os.getenv('MYSQL_SSL_CA')
    connect_kwargs = dict(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

    if ssl_ca:
        connect_kwargs['ssl'] = {'ca': ssl_ca}

    return pymysql.connect(**connect_kwargs)

def get_local_db_connection():
    """
    Crea y retorna una conexión a la base de datos MySQL LOCAL.
    Para datos del sistema de tickets.
    """
    try:
        # Optional SSL/TLS for local/remote DB: provide MYSQL_SSL_CA or LOCAL_DB_SSL_CA
        local_ssl_ca = os.getenv('LOCAL_DB_SSL_CA') or os.getenv('MYSQL_SSL_CA')
        local_kwargs = dict(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'sistema_ticket_recrear'),
            port=int(os.getenv('DB_PORT', 3306)),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )

        if local_ssl_ca:
            local_kwargs['ssl'] = {'ca': local_ssl_ca}

        connection = pymysql.connect(**local_kwargs)
        return connection
    except pymysql.Error as e:
        print(f"Error al conectar a la base de datos LOCAL: {e}")
        raise

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Ejecuta una query de forma segura con manejo de errores.
    Usa la base de datos LOCAL.
    
    Args:
        query: La consulta SQL a ejecutar
        params: Parámetros para la consulta (opcional)
        fetch_one: Si True, retorna un solo resultado
        fetch_all: Si True, retorna todos los resultados
        commit: Si True, hace commit de la transacción
    
    Returns:
        El resultado de la consulta según los parámetros
    """
    conn = None
    cursor = None
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, params or ())
        
        if commit:
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else True
        
        if fetch_one:
            return cursor.fetchone()
        
        if fetch_all:
            return cursor.fetchall()
        
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error ejecutando query: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
