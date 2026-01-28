Ejecucion
Windows — PowerShell

Si solo quieres web + webhook (sin IMAP), basta con:
cd C:\Users\Usuario\Desktop\gestion_ticket
.\.venv\Scripts\Activate.ps1
$env:FLASK_PORT="5003"
py run.py


Para encender todo (web + IMAP) en Windows, ejecuta:

cd C:\Users\Usuario\Desktop\gestion_ticket
.\.venv\Scripts\Activate.ps1
$env:FLASK_PORT="5003"
py run.py


Polling manual (para Programador de tareas)

cd C:\Users\Usuario\Desktop\gestion_ticket
\.venv\Scripts\Activate.ps1
$env:IMAP_SEARCH="ALL"  # usa "UNSEEN" si solo quieres no leídos
py poll_email_once.py

Linux

cd /ruta/gestion_ticket
source .venv/bin/activate
export START_EMAIL_POLLER=1
export EMAIL_KEEPALIVE=300
export EMAIL_MIN_BACKOFF=5
export EMAIL_MAX_BACKOFF=600
python3 run.py