"""
Modelo para manejo de Respuestas Rápidas (Quick Replies)
"""

from flask_app.config.conexion_login import get_local_db_connection
import pymysql.cursors
import logging

class RespuestaRapidaModel:
    
    @staticmethod
    def obtener_por_operador(id_operador):
        """
        Obtiene las respuestas rápidas de un operador específico
        Incluye 3 respuestas estándar del sistema (visibilidad='Publico')
        más las respuestas personales del operador (visibilidad='Privado')
        
        Args:
            id_operador: ID del operador
            
        Returns:
            list: Lista de respuestas rápidas
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Obtener información del operador para usar en variables
            cursor.execute("""
                SELECT nombre, email 
                FROM operador 
                WHERE id_operador = %s
            """, (id_operador,))
            operador = cursor.fetchone()
            
            if not operador:
                return []
            
            nombre_operador = operador['nombre'].split()[0]  # Primer nombre
            
            # Obtener respuestas públicas (estándar para todos) y privadas del operador
            query = """
                SELECT 
                    id_respuesta,
                    titulo,
                    contenido,
                    categoria,
                    visibilidad,
                    veces_usada
                FROM respuesta_rapida
                WHERE deleted_at IS NULL
                  AND activa = 1
                  AND (visibilidad = 'Publico' OR respuesta_operador = %s)
                ORDER BY 
                    visibilidad DESC,  -- Públicas primero
                    veces_usada DESC,  -- Más usadas primero
                    titulo ASC
            """
            
            cursor.execute(query, (id_operador,))
            respuestas = cursor.fetchall()
            
            # Reemplazar variables en el contenido
            for respuesta in respuestas:
                contenido = respuesta['contenido']
                contenido = contenido.replace('{nombre_operador}', nombre_operador)
                contenido = contenido.replace('{operador}', nombre_operador)
                respuesta['contenido'] = contenido
            
            return respuestas
            
        except Exception as e:
            logging.error(f"Error al obtener respuestas rápidas del operador {id_operador}: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def incrementar_uso(id_respuesta):
        """
        Incrementa el contador de veces usada de una respuesta rápida
        
        Args:
            id_respuesta: ID de la respuesta rápida
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE respuesta_rapida 
                SET veces_usada = veces_usada + 1
                WHERE id_respuesta = %s
            """, (id_respuesta,))
            
            conn.commit()
            logging.info(f"Respuesta rápida #{id_respuesta} usada")
            
        except Exception as e:
            logging.error(f"Error al incrementar uso de respuesta rápida #{id_respuesta}: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def crear_respuestas_estandar():
        """
        Crea las 3 respuestas rápidas estándar del sistema si no existen
        Estas respuestas son públicas y están disponibles para todos los operadores
        """
        conn = None
        cursor = None
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Usar id_operador = 1 como operador del sistema para las respuestas públicas
            respuestas_estandar = [
                {
                    'titulo': 'Saludo Inicial',
                    'contenido': 'Hola, gracias por contactarnos. Mi nombre es {nombre_operador} y estaré ayudándote con tu solicitud.',
                    'categoria': 'Saludo'
                },
                {
                    'titulo': 'Solicitar Información',
                    'contenido': 'Para poder ayudarte mejor, necesito que me proporciones más información sobre tu solicitud. ¿Podrías darme más detalles?',
                    'categoria': 'Seguimiento'
                },
                {
                    'titulo': 'Ticket Resuelto',
                    'contenido': 'Me alegra que hayamos podido resolver tu problema. Si tienes alguna otra consulta, no dudes en contactarnos. ¡Que tengas un excelente día!',
                    'categoria': 'Cierre'
                }
            ]
            
            for respuesta in respuestas_estandar:
                # Verificar si ya existe
                cursor.execute("""
                    SELECT id_respuesta 
                    FROM respuesta_rapida 
                    WHERE titulo = %s AND visibilidad = 'Publico'
                """, (respuesta['titulo'],))
                
                if not cursor.fetchone():
                    # Insertar nueva respuesta estándar
                    cursor.execute("""
                        INSERT INTO respuesta_rapida 
                        (respuesta_operador, titulo, contenido, categoria, visibilidad, activa)
                        VALUES (1, %s, %s, %s, 'Publico', 1)
                    """, (respuesta['titulo'], respuesta['contenido'], respuesta['categoria']))
            
            conn.commit()
            logging.info("Respuestas rápidas estándar verificadas/creadas")
            
        except Exception as e:
            logging.error(f"Error al crear respuestas rápidas estándar: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
