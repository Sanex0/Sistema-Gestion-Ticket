import pymysql

def get_db_connection():
    DB_HOST = '181.212.204.13'
    DB_USER = 'sistemasu'
    DB_PASS = '5rTF422.3E'
    DB_NAME = 'sistemas'  # Cambia esto por el nombre real de la base de datos
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
