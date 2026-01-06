from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_app.models.adjunto_model import AdjuntoModel
from flask_app.models.mensaje_model import MensajeModel
from flask_app.models.ticket_model import TicketModel
from flask_app.utils.jwt_utils import token_requerido
from flask_app.utils.error_handler import manejar_errores, validar_campos_requeridos, ValidationError, NotFoundError
import os

adjunto_bp = Blueprint('adjunto', __name__, url_prefix='/api')


@adjunto_bp.route('/tickets/<int:ticket_id>/adjuntos', methods=['GET'])
@manejar_errores
def listar_adjuntos_ticket(ticket_id):
    """
    Lista todos los adjuntos de un ticket.
    
    GET /api/tickets/{ticket_id}/adjuntos
    
    Response:
    {
        "success": true,
        "adjuntos": [...],
        "total": 5
    }
    """
    adjuntos = AdjuntoModel.listar_por_ticket(ticket_id)
    
    return jsonify({
        'success': True,
        'adjuntos': adjuntos,
        'total': len(adjuntos)
    }), 200


@adjunto_bp.route('/mensajes/<int:mensaje_id>/adjuntos', methods=['GET'])
@manejar_errores
def listar_adjuntos_mensaje(mensaje_id):
    """
    Lista todos los adjuntos de un mensaje.
    
    GET /api/mensajes/{mensaje_id}/adjuntos
    
    Response:
    {
        "success": true,
        "adjuntos": [...],
        "total": 2
    }
    """
    # Verificar que el mensaje existe
    mensaje = MensajeModel.buscar_por_id(mensaje_id)
    if not mensaje:
        raise NotFoundError(f"Mensaje con ID {mensaje_id} no encontrado")
    
    adjuntos = AdjuntoModel.listar_por_mensaje(mensaje_id)
    
    return jsonify({
        'success': True,
        'adjuntos': adjuntos,
        'total': len(adjuntos)
    }), 200


@adjunto_bp.route('/mensajes/<int:mensaje_id>/adjuntos', methods=['POST'])
@manejar_errores
@token_requerido
def subir_adjunto(operador_actual, mensaje_id):
    """
    Sube un archivo adjunto a un mensaje.
    
    POST /api/mensajes/{mensaje_id}/adjuntos
    Content-Type: multipart/form-data
    Body:
        - file: archivo a subir
    
    Response:
    {
        "success": true,
        "mensaje": "Archivo subido exitosamente",
        "adjunto": {
            "id_adj": 1,
            "nom_adj": "documento.pdf",
            "ruta": "/uploads/ticket_1/20251229_103045_abc123.pdf"
        }
    }
    """
    # Verificar que el mensaje existe
    mensaje = MensajeModel.buscar_por_id(mensaje_id)
    if not mensaje:
        raise NotFoundError(f"Mensaje con ID {mensaje_id} no encontrado")

    # Validar permisos de escritura sobre el ticket
    ticket_id = mensaje.get('id_ticket')
    if not TicketModel.operador_puede_escribir_ticket(ticket_id, operador_actual):
        raise ValidationError('No tiene permisos para adjuntar archivos en este ticket')
    
    # Verificar que se envió un archivo
    if 'file' not in request.files:
        raise ValidationError("No se encontró el archivo en la petición")
    
    file = request.files['file']
    
    # Verificar que el archivo tiene nombre
    if file.filename == '':
        raise ValidationError("El archivo no tiene nombre")
    
    # Validar el archivo
    es_valido, mensaje_error = AdjuntoModel.validar_archivo(file.filename)
    if not es_valido:
        raise ValidationError(mensaje_error)
    
    # Generar nombre único
    filename = secure_filename(file.filename)
    unique_filename = AdjuntoModel.generar_nombre_unico(filename)
    
    # Obtener directorio del ticket
    id_ticket = mensaje['id_ticket']
    ticket_dir = AdjuntoModel.obtener_ruta_por_ticket(id_ticket)
    
    # Ruta completa del archivo
    file_path = os.path.join(ticket_dir, unique_filename)
    
    # Guardar archivo
    file.save(file_path)
    
    # Registrar en base de datos
    adjunto_data = {
        'nom_adj': filename,  # Nombre original
        'ruta': file_path,
        'id_msg': mensaje_id
    }
    
    resultado = AdjuntoModel.crear_adjunto(adjunto_data)
    
    return jsonify({
        'success': True,
        'mensaje': 'Archivo subido exitosamente',
        'adjunto': {
            'id_adj': resultado['id_adj'],
            'nom_adj': filename,
            'ruta': file_path
        }
    }), 201


@adjunto_bp.route('/adjuntos/<int:adjunto_id>', methods=['GET'])
@manejar_errores
def obtener_adjunto(adjunto_id):
    """
    Obtiene información de un adjunto.
    
    GET /api/adjuntos/{adjunto_id}
    
    Response:
    {
        "success": true,
        "adjunto": {...}
    }
    """
    adjunto = AdjuntoModel.buscar_por_id(adjunto_id)
    
    if not adjunto:
        raise NotFoundError(f"Adjunto con ID {adjunto_id} no encontrado")
    
    return jsonify({
        'success': True,
        'adjunto': adjunto
    }), 200


@adjunto_bp.route('/adjuntos/<int:adjunto_id>/download', methods=['GET'])
@manejar_errores
def descargar_adjunto(adjunto_id):
    """
    Descarga un archivo adjunto.
    
    GET /api/adjuntos/{adjunto_id}/download
    
    Response: Archivo binario
    """
    adjunto = AdjuntoModel.buscar_por_id(adjunto_id)
    
    if not adjunto:
        raise NotFoundError(f"Adjunto con ID {adjunto_id} no encontrado")
    
    # Verificar que el archivo existe
    if not os.path.exists(adjunto['ruta']):
        raise NotFoundError(f"Archivo físico no encontrado: {adjunto['nom_adj']}")
    
    # Enviar archivo
    return send_file(
        adjunto['ruta'],
        as_attachment=True,
        download_name=adjunto['nom_adj']
    )


@adjunto_bp.route('/adjuntos/<int:adjunto_id>', methods=['DELETE'])
@token_requerido
@manejar_errores
def eliminar_adjunto(adjunto_id, operador_actual):
    """
    Elimina un adjunto.
    
    DELETE /api/adjuntos/{adjunto_id}
    Headers:
        - Authorization: Bearer {token}
    Query params:
        - permanente: bool (default: false) - Eliminar permanentemente
    
    Response:
    {
        "success": true,
        "mensaje": "Adjunto eliminado exitosamente"
    }
    """
    adjunto = AdjuntoModel.buscar_por_id(adjunto_id)
    
    if not adjunto:
        raise NotFoundError(f"Adjunto con ID {adjunto_id} no encontrado")
    
    permanente = request.args.get('permanente', 'false').lower() == 'true'
    
    # Solo admin puede eliminar permanentemente
    if permanente and operador_actual.get('rol') != 'Admin':
        raise ValidationError("Solo los administradores pueden eliminar adjuntos permanentemente")
    
    id_operador = operador_actual.get('id_operador')
    AdjuntoModel.eliminar_adjunto(adjunto_id, deleted_by=id_operador, soft_delete=not permanente)
    
    return jsonify({
        'success': True,
        'mensaje': 'Adjunto eliminado exitosamente'
    }), 200


@adjunto_bp.route('/tickets/<int:ticket_id>/adjuntos/estadisticas', methods=['GET'])
@manejar_errores
def estadisticas_adjuntos(ticket_id):
    """
    Obtiene estadísticas de adjuntos de un ticket.
    
    GET /api/tickets/{ticket_id}/adjuntos/estadisticas
    
    Response:
    {
        "success": true,
        "estadisticas": {
            "total_adjuntos": 10,
            "mensajes_con_adjuntos": 5,
            "adjuntos_activos": 8,
            "adjuntos_eliminados": 2
        }
    }
    """
    estadisticas = AdjuntoModel.obtener_estadisticas_ticket(ticket_id)
    
    return jsonify({
        'success': True,
        'estadisticas': estadisticas
    }), 200
