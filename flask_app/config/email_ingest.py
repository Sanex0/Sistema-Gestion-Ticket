"""
Configuración de ejemplo para el ingestor de email (IMAP).

Rellena `IMAP` con los datos reales de la cuenta de prueba en cPanel.
`ADDRESS_MAPPING` mapea direcciones de correo (recipients) a `id_depto` en la DB.
"""


IMAP = {
    'HOST': 'imap.gmail.com',
    'PORT': 993,
    'USER': 'soporteticketrecrear@gmail.com',
    'PASSWORD': 'wlfp ecri riqs oeaa',
    'USE_SSL': True,
    'FOLDER': 'INBOX',
    # Search criteria for IMAP (default: UNSEEN). Use ALL to process even read emails.
    'SEARCH': 'UNSEEN'
}

# Mapeo simple: email -> id_depto (ajusta el id si tu depto tiene otro id)
ADDRESS_MAPPING = {
    'soporteticketrecrear@gmail.com': 1,
}

# Opciones SMTP para enviar respuestas automáticas (usa la misma cuenta por defecto)
SMTP = {
    'HOST': 'smtp.gmail.com',
    'PORT': 587,
    'USER': IMAP['USER'],
    'PASSWORD': IMAP['PASSWORD'],
    'USE_TLS': True,
    'FROM_NAME': 'Soporte',
    'FROM_ADDRESS': IMAP['USER']
}

# Habilitar/deshabilitar envío de respuesta automática
SEND_AUTOREPLY = True

# Intervalo de polling en segundos (si se usa polling)
POLL_INTERVAL = 60
