import json
from flask_app.config.conexion_login import execute_query

rows = execute_query('''
SELECT t.id_ticket, t.titulo, t.id_depto, t.id_operador_emisor, t.id_canal, t.id_usuarioext, t.fecha_ini
FROM ticket t
WHERE t.id_canal = 1 AND t.fecha_ini >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
ORDER BY t.fecha_ini DESC
LIMIT 100
''', fetch_all=True) or []
print(json.dumps(rows, default=str, ensure_ascii=False, indent=2))
