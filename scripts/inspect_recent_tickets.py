import json
from flask_app.config.conexion_login import execute_query

rows = execute_query("""
SELECT t.id_ticket, t.titulo, t.fecha_ini, ue.email as usuario_email, m.id_msg, m.asunto, m.fecha_envio
FROM ticket t
LEFT JOIN usuario_ext ue ON t.id_usuarioext = ue.id_usuario
LEFT JOIN mensaje m ON m.id_ticket = t.id_ticket
WHERE t.fecha_ini >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
ORDER BY t.fecha_ini DESC
LIMIT 100
""", fetch_all=True) or []
print(json.dumps(rows, default=str, ensure_ascii=False, indent=2))
