// ============================================
// GESTIÓN DE TICKETS Y CHAT
// Archivo limpio y organizado
// ============================================

// Variables globales
window.currentTicketId = null;
window.chatMessages = [];
window.pollingInterval = null;
window.lastMessageId = null;
window.currentOperadorId = null;

// ============================================
// FUNCIÓN PARA CREAR TICKET
// ============================================

window.createTicket = async function() {
    var form = document.getElementById('newTicketForm');
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    var operadorSelect = document.getElementById('ticketOperadorAsignado');
    var idOperadorAsignado = operadorSelect ? operadorSelect.value : null;

    var deptoSelect = document.getElementById('ticketDepartamento');
    var idDepto = deptoSelect ? deptoSelect.value : null;
    
    var ticketData = {
        titulo: document.getElementById('ticketSubject').value,
        descripcion: document.getElementById('ticketDescription').value,
        id_prioridad: getPriorityId(document.getElementById('ticketPriority').value),
        id_estado: 1,
        id_club: (window.catalogos && window.catalogos.clubes && window.catalogos.clubes[0]) ? window.catalogos.clubes[0].id_club : 1,
        id_sla: (window.catalogos && window.catalogos.slas && window.catalogos.slas[0]) ? window.catalogos.slas[0].id_sla : 1,
        tipo_ticket: 'Publico',
        id_depto: idDepto ? parseInt(idDepto) : null,
        id_operador_asignado: idOperadorAsignado ? parseInt(idOperadorAsignado) : null,
        mensaje: {
            asunto: document.getElementById('ticketSubject').value,
            contenido: document.getElementById('ticketDescription').value,
            id_canal: 2
        }
    };

    var userField = document.getElementById('ticketUser');
    if (userField && userField.value) {
        ticketData.usuario_nombre = userField.value;
    }

    try {
        console.log('📤 Enviando ticket:', ticketData);
        var result = await DashboardAPI.createTicket(ticketData);
        console.log('✅ Respuesta:', result);
        
        if (result.success) {
            showToast('✅ Ticket creado correctamente', 'success');
            
            var modal = bootstrap.Modal.getInstance(document.getElementById('newTicketModal'));
            if (modal) modal.hide();
            
            form.reset();
            
            var attachmentList = document.getElementById('attachmentList');
            var attachmentCount = document.getElementById('attachmentCount');
            if (attachmentList) attachmentList.innerHTML = '';
            if (attachmentCount) attachmentCount.textContent = '0';
            
            if (typeof cargarTicketsReales === 'function') {
                await cargarTicketsReales();
            }
        } else {
            showToast('❌ ' + (result.message || 'Error al crear ticket'), 'warning');
        }
    } catch (error) {
        console.error('❌ Error:', error);
        showToast('❌ Error de conexión: ' + error.message, 'warning');
    }
};

function getPriorityId(priorityText) {
    if (priorityText === null || priorityText === undefined) return 3;

    // Soportar values numéricos del <select> (#ticketPriority):
    // 1 Urgente, 2 Alta, 3 Media, 4 Baja
    var numeric = parseInt(priorityText, 10);
    if (!isNaN(numeric) && numeric >= 1 && numeric <= 4) return numeric;

    // Soportar textos (por si llega desde otros flujos)
    var key = String(priorityText).toLowerCase().trim();
    if (key === '1' || key === 'urgente') return 1;
    if (key === '2' || key === 'alta') return 2;
    if (key === '3' || key === 'media' || key === 'normal') return 3;
    if (key === '4' || key === 'baja') return 4;
    if (key === 'critica' || key === 'crítica') return 1;
    return 3;
}

// ============================================
// VER TICKET Y CARGAR MENSAJES
// ============================================

window.verTicket = async function(idTicket) {
    // Unificar flujo: si existe seleccionarTicket (tickets-reales.js), usarlo.
    // Esto evita inconsistencias entre tabla "recientes" y cards.
    if (typeof seleccionarTicket === 'function') {
        try {
            return await seleccionarTicket(idTicket);
        } catch (e) {
            console.error('[verTicket->seleccionarTicket] Error:', e);
        }
    }

    try {
        console.log('[verTicket] Abriendo ticket #' + idTicket);

        // Detener polling anterior si existe
        detenerPollingMensajes();

        // IMPORTANTE: Limpiar mensajes del ticket anterior
        window.chatMessages = [];

        // Actualizar ID del ticket actual
        window.currentTicketId = idTicket;

        var result = await DashboardAPI.getTicketById(idTicket);

        if (result.success && result.data) {
            mostrarDetalleTicketEnChat(result.data);
            await cargarMensajesTicket(idTicket);

            // Iniciar polling para actualizaciones automáticas
            iniciarPollingMensajes(idTicket);
        }
    } catch (error) {
        console.error('[verTicket] Error:', error);
        showToast('❌ No se pudo cargar el ticket', 'warning');
    }
};

function mostrarDetalleTicketEnChat(ticket) {
    var ticketTitle = document.querySelector('.ticket-detail-header h5');
    if (ticketTitle) {
        var estadoBadge = obtenerBadgeEstado(ticket.estado);
        var prioridadBadge = obtenerBadgePrioridad(ticket.prioridad);
        
        ticketTitle.innerHTML = '<div class="d-flex align-items-center gap-2 flex-wrap">' +
            '<i class="bi bi-ticket-perforated-fill"></i>' +
            '<span>Ticket #' + ticket.id_ticket + ' - ' + ticket.titulo + '</span>' +
            estadoBadge + prioridadBadge +
            '</div>';
    }

    var userInfo = document.querySelector('.ticket-user-info');
    if (userInfo) {
        var nombre = (ticket.usuario && ticket.usuario.nombre) ? ticket.usuario.nombre : 'Sin usuario';
        var email = (ticket.usuario && ticket.usuario.email) ? ticket.usuario.email : '';
        userInfo.innerHTML = '<div class="d-flex align-items-center gap-3">' +
            '<i class="bi bi-person-circle fs-2 text-brand-blue"></i>' +
            '<div><div class="fw-bold">' + nombre + '</div>' +
            '<small class="text-muted">' + email + '</small></div></div>';
    }

    // Alinear bloqueo del chat también en este flujo (tabla de tickets recientes)
    try {
        var currentUser = (typeof AuthService !== 'undefined' && AuthService.getCurrentUser)
            ? AuthService.getCurrentUser()
            : null;
        var currentOperadorId = currentUser ? (currentUser.operador_id || currentUser.id_operador || currentUser.id) : null;
        var currentRol = currentUser ? (currentUser.rol || currentUser.rol_nombre || '') : '';
        var isAdmin = String(currentRol).toLowerCase().trim() === 'admin';

        var ownerIdRaw = (ticket && (ticket.id_operador_owner ?? ticket.id_operador ?? ticket.id_operador_asignado)) ?? null;
        var ownerId = ownerIdRaw !== null && ownerIdRaw !== undefined ? parseInt(ownerIdRaw, 10) : null;

        var emisorIdRaw = (ticket && ticket.id_operador_emisor) ?? null;
        var emisorId = emisorIdRaw !== null && emisorIdRaw !== undefined ? parseInt(emisorIdRaw, 10) : null;

        var currentIdInt = currentOperadorId !== null && currentOperadorId !== undefined ? parseInt(currentOperadorId, 10) : null;
        var esOwner = !!(ownerId && currentIdInt && ownerId === currentIdInt);
        var esEmisor = !!(emisorId && currentIdInt && emisorId === currentIdInt);

        var sinAsignar = !ownerId;

        // Regla alineada al backend:
        // - Admin: puede escribir (si no cerrado)
        // - Owner: puede escribir
        // - Emisor: puede escribir (aunque otro sea Owner)
        var puedeEscribir = !!(!isAdmin ? (esOwner || esEmisor) : true);
        var noResponsable = !!(ownerId && !puedeEscribir);
        var idEstado = ticket?.id_estado;
        var estadoTxt = String(ticket?.estado || ticket?.estado_desc || '').toLowerCase().trim();
        var cerrado = (String(idEstado) === '4') || (estadoTxt === 'cerrado');

        // Si es emisor/admin, no bloquear aunque esté sin asignar
        window.chatBloqueadoPorNoTomado = !!(sinAsignar && !esEmisor && !isAdmin);
        window.chatBloqueadoPorNoResponsable = !!noResponsable;
        window.chatBloqueadoPorCerrado = !!cerrado;

        var inputDesktop = document.getElementById('chatMessageInputDesktop');
        var inputMobile = document.getElementById('chatMessageInput');
        var btnDesktop = inputDesktop ? inputDesktop.nextElementSibling : null;
        var btnMobile = inputMobile ? inputMobile.nextElementSibling : null;

        var placeholder = cerrado
            ? 'Ticket cerrado: no se puede responder.'
            : (sinAsignar
                ? (esEmisor || isAdmin ? 'Escribe un mensaje...' : 'Debes tomar el ticket para responder...')
                : (noResponsable ? 'Solo el responsable o el emisor del ticket pueden responder.' : 'Escribe un mensaje...'));

        var enabled = !window.chatBloqueadoPorNoTomado && !noResponsable && !cerrado;

        var setEnabled = function(inputEl, btnEl) {
            if (inputEl) {
                inputEl.disabled = !enabled;
                inputEl.placeholder = placeholder;
            }
            if (btnEl && btnEl.tagName === 'BUTTON') {
                btnEl.disabled = !enabled;
                if (!enabled) {
                    btnEl.setAttribute('aria-disabled', 'true');
                } else {
                    btnEl.removeAttribute('aria-disabled');
                }
            }
        };

        setEnabled(inputDesktop, btnDesktop);
        setEnabled(inputMobile, btnMobile);
    } catch (e) {
        console.warn('[mostrarDetalleTicketEnChat] No se pudo actualizar bloqueo chat:', e);
    }
}

function obtenerBadgeEstado(estado) {
    var estados = {
        'Nuevo': 'badge bg-info',
        'En Progreso': 'badge bg-warning',
        'En Proceso': 'badge bg-warning',
        'Resuelto': 'badge bg-success',
        'Cerrado': 'badge bg-secondary'
    };
    var clase = estados[estado] || 'badge bg-secondary';
    return '<span class="' + clase + '">' + (estado || 'Sin estado') + '</span>';
}

function obtenerBadgePrioridad(prioridad) {
    var prioridades = {
        'Baja': 'badge bg-light text-dark',
        'Media': 'badge bg-primary',
        'Alta': 'badge bg-warning text-dark',
        'Critica': 'badge bg-danger'
    };
    var clase = prioridades[prioridad] || 'badge bg-secondary';
    return '<span class="' + clase + '"><i class="bi bi-exclamation-circle"></i> ' + (prioridad || '') + '</span>';
}

// ============================================
// CARGAR Y RENDERIZAR MENSAJES
// ============================================

async function cargarMensajesTicket(idTicket) {
    try {
        console.log('[cargarMensajes] Cargando mensajes para ticket #' + idTicket);
        var result = await DashboardAPI.getMensajesPorTicket(idTicket);
        
        if (result && result.success && Array.isArray(result.data)) {
            console.log('[cargarMensajes] Recibidos ' + result.data.length + ' mensajes desde API');
            
            // Verificar si hay mensajes nuevos antes de actualizar
            var hayNuevos = false;
            if (window.chatMessages.length === 0 || result.data.length !== window.chatMessages.length) {
                hayNuevos = true;
                console.log('[cargarMensajes] Hay cambios: longitud actual=' + window.chatMessages.length + ', nueva=' + result.data.length);
            } else if (result.data.length > 0 && window.chatMessages.length > 0) {
                var ultimoActual = window.chatMessages[window.chatMessages.length - 1];
                var ultimoNuevo = result.data[result.data.length - 1];
                if (ultimoActual.id_msg !== ultimoNuevo.id_msg) {
                    hayNuevos = true;
                    console.log('[cargarMensajes] Mensaje nuevo detectado: ' + ultimoNuevo.id_msg);
                }
            }
            
            if (hayNuevos) {
                console.log('[cargarMensajes] Renderizando ' + result.data.length + ' mensajes');
                renderizarMensajes(result.data);
            } else {
                console.log('[cargarMensajes] No hay cambios, no se actualiza');
            }
        } else {
            console.warn('[cargarMensajes] Respuesta inválida:', result);
        }
    } catch (error) {
        console.error('[cargarMensajes] Error:', error);
    }
}

function renderizarMensajes(mensajes) {
    console.log('[renderizarMensajes] Renderizando ' + mensajes.length + ' mensajes');
    var chatContainer = document.getElementById('chatMessagesDesktop');
    var chatContainerMobile = document.getElementById('chatMessages');
    
    if (!mensajes || mensajes.length === 0) {
        var emptyHTML = '<div class="empty-state py-5 text-center">' +
            '<i class="bi bi-chat-dots display-1 text-muted opacity-25"></i>' +
            '<p class="text-muted mt-3">No hay mensajes en este ticket</p></div>';
        if (chatContainer) chatContainer.innerHTML = emptyHTML;
        if (chatContainerMobile) chatContainerMobile.innerHTML = emptyHTML;
        window.chatMessages = [];
        console.log('[renderizarMensajes] No hay mensajes, mostrando estado vacío');
        return;
    }

    // Obtener ID del operador actual
    if (!window.currentOperadorId) {
        var currentUser = AuthService.getCurrentUser();
        if (currentUser) {
            window.currentOperadorId = currentUser.id;
        }
    }
    
    // Verificar que todos los mensajes son del ticket actual
    var ticketIdActual = window.currentTicketId;
    console.log('[renderizarMensajes] Filtrando mensajes para ticket #' + ticketIdActual);
    
    var mensajesFiltrados = mensajes.filter(function(msg) {
        return msg.id_ticket === ticketIdActual;
    });
    
    if (mensajesFiltrados.length !== mensajes.length) {
        console.warn('⚠️ Se detectaron ' + (mensajes.length - mensajesFiltrados.length) + ' mensajes de otros tickets. Filtrando...');
        console.log('[renderizarMensajes] Mensajes antes de filtrar:', mensajes.map(function(m) { return {id: m.id_msg, ticket: m.id_ticket}; }));
        mensajes = mensajesFiltrados;
    }
    
    console.log('[renderizarMensajes] Mensajes después de filtrar: ' + mensajes.length);

    // Si es la primera carga o el chat está vacío, renderizar todo
    var esPrimeraCarga = (window.chatMessages.length === 0);
    console.log('[renderizarMensajes] Es primera carga: ' + esPrimeraCarga + ' (chatMessages.length=' + window.chatMessages.length + ')');
    
    if (esPrimeraCarga) {
        console.log('[renderizarMensajes] Renderizando todos los mensajes desde cero');
        var mensajesHTML = '';
        
        for (var i = 0; i < mensajes.length; i++) {
            mensajesHTML += crearMensajeHTML(mensajes[i]);
        }
        
        if (chatContainer) {
            chatContainer.innerHTML = mensajesHTML;
            chatContainer.scrollTop = chatContainer.scrollHeight;
            console.log('[renderizarMensajes] Chat desktop actualizado con ' + mensajes.length + ' mensajes');
        }
        if (chatContainerMobile) {
            chatContainerMobile.innerHTML = mensajesHTML;
            chatContainerMobile.scrollTop = chatContainerMobile.scrollHeight;
        }
        
        window.chatMessages = mensajes;
        console.log('[renderizarMensajes] window.chatMessages actualizado con ' + mensajes.length + ' mensajes');
        return;
    }
    
    // Solo agregar mensajes nuevos (polling actualización)
    var mensajesNuevos = [];
    var ultimoIdActual = window.chatMessages.length > 0 ? window.chatMessages[window.chatMessages.length - 1].id_msg : 0;
    
    for (var i = 0; i < mensajes.length; i++) {
        if (mensajes[i].id_msg > ultimoIdActual) {
            mensajesNuevos.push(mensajes[i]);
        }
    }
    
    // Si hay mensajes nuevos, agregarlos al final sin recargar todo
    if (mensajesNuevos.length > 0) {
        var isAtBottomDesktop = chatContainer ? (chatContainer.scrollHeight - chatContainer.scrollTop <= chatContainer.clientHeight + 100) : true;
        var isAtBottomMobile = chatContainerMobile ? (chatContainerMobile.scrollHeight - chatContainerMobile.scrollTop <= chatContainerMobile.clientHeight + 100) : true;
        
        for (var i = 0; i < mensajesNuevos.length; i++) {
            var nuevoMensajeHTML = crearMensajeHTML(mensajesNuevos[i]);
            
            // Crear elemento temporal para agregar al DOM
            if (chatContainer) {
                var tempDiv = document.createElement('div');
                tempDiv.innerHTML = nuevoMensajeHTML;
                var nuevoElemento = tempDiv.firstChild;
                nuevoElemento.style.opacity = '0';
                nuevoElemento.style.transform = 'translateY(10px)';
                nuevoElemento.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                chatContainer.appendChild(nuevoElemento);
                
                // Animación fade-in
                setTimeout(function(elemento) {
                    elemento.style.opacity = '1';
                    elemento.style.transform = 'translateY(0)';
                }, 10, nuevoElemento);
                
                if (isAtBottomDesktop) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }
            
            if (chatContainerMobile) {
                var tempDivMobile = document.createElement('div');
                tempDivMobile.innerHTML = nuevoMensajeHTML;
                var nuevoElementoMobile = tempDivMobile.firstChild;
                nuevoElementoMobile.style.opacity = '0';
                nuevoElementoMobile.style.transform = 'translateY(10px)';
                nuevoElementoMobile.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                chatContainerMobile.appendChild(nuevoElementoMobile);
                
                setTimeout(function(elemento) {
                    elemento.style.opacity = '1';
                    elemento.style.transform = 'translateY(0)';
                }, 10, nuevoElementoMobile);
                
                if (isAtBottomMobile) {
                    chatContainerMobile.scrollTop = chatContainerMobile.scrollHeight;
                }
            }
        }
        
        window.chatMessages = mensajes;
    }
}

// Función auxiliar para crear el HTML de un mensaje
function crearMensajeHTML(msg) {
    var esMensajePropio = false;
    if (msg.remitente_tipo === 'Operador' && window.currentOperadorId) {
        esMensajePropio = (msg.remitente_id === window.currentOperadorId);
    }
    
    var nombreRemitente = msg.remitente_nombre || (msg.remitente_tipo === 'Operador' ? 'Operador' : 'Usuario Externo');
    var hora = formatearHora(msg.fecha_envio);
    
    if (esMensajePropio) {
        return '<div class="message-wrapper message-right" data-msg-id="' + msg.id_msg + '">' +
            '<div class="message-content">' +
            '<div class="message-bubble message-bubble-right">' +
            '<div class="message-sender">Tú (' + nombreRemitente + ')</div>' +
            '<p class="mb-1">' + msg.contenido + '</p>' +
            '<small class="message-time">' + hora + '</small>' +
            '</div></div></div>';
    } else {
        var tipoLabel = msg.remitente_tipo === 'Usuario' ? 'Usuario Externo' : 'Operador';
        return '<div class="message-wrapper message-left" data-msg-id="' + msg.id_msg + '">' +
            '<div class="message-content">' +
            '<div class="message-bubble message-bubble-left">' +
            '<div class="message-sender">' + nombreRemitente + ' (' + tipoLabel + ')</div>' +
            '<p class="mb-1">' + msg.contenido + '</p>' +
            '<small class="message-time">' + hora + '</small>' +
            '</div></div></div>';
    }
}

// ============================================
// ENVIAR MENSAJE
// ============================================

window.enviarMensaje = async function(messageText) {
    var inputDesktop = document.getElementById('chatMessageInputDesktop');
    var inputMobile = document.getElementById('chatMessageInput');
    
    var mensaje = messageText || (inputDesktop ? inputDesktop.value : '') || (inputMobile ? inputMobile.value : '');
    
    if (!mensaje || !mensaje.trim()) {
        showToast('⚠️ Escribe un mensaje antes de enviar', 'warning');
        return;
    }

    if (!window.currentTicketId) {
        showToast('❌ No hay un ticket seleccionado', 'warning');
        return;
    }

    // Regla: no se puede escribir/mandar mensajes si el ticket no fue tomado (sin asignar)
    if (window.chatBloqueadoPorNoTomado) {
        showToast('⏳ Debes tomar el ticket antes de responder', 'warning');
        return;
    }

    // Regla: no se puede escribir si el ticket está asignado a otro operador
    if (window.chatBloqueadoPorNoResponsable) {
        showToast('⛔ Solo el responsable o el emisor del ticket pueden responder', 'warning');
        return;
    }

    // Regla: no se puede escribir si el ticket está cerrado
    if (window.chatBloqueadoPorCerrado) {
        showToast('🔒 El ticket está cerrado. No puedes enviar mensajes.', 'warning');
        return;
    }

    try {
        var result = await DashboardAPI.enviarMensaje({
            id_ticket: window.currentTicketId,
            contenido: mensaje.trim(),
            id_canal: 2,
            es_interno: false
        });

        if (!result) {
            showToast('❌ Sesión no válida. Vuelve a iniciar sesión.', 'warning');
            return;
        }
        
        if (result.success) {
            if (inputDesktop) inputDesktop.value = '';
            if (inputMobile) inputMobile.value = '';
            await cargarMensajesTicket(window.currentTicketId);
            showToast('✅ Mensaje enviado', 'success');
        } else {
            var msg = result.mensaje || result.message || result.error || 'Error al enviar';
            showToast('❌ ' + msg, 'warning');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('❌ Error de conexión', 'warning');
    }
};

// ============================================
// RESPUESTAS RÁPIDAS
// ============================================

window.toggleQuickRepliesDesktop = function() {
    var panel = document.getElementById('quickRepliesInlineDesktop');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
};

window.insertQuickReplyDesktop = function(text) {
    var input = document.getElementById('chatMessageInputDesktop');
    if (input) {
        input.value = text;
        input.focus();
    }
    window.toggleQuickRepliesDesktop();
};

window.toggleQuickReplies = function() {
    var panel = document.getElementById('quickRepliesInline');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
};

window.insertQuickReply = function(text) {
    var input = document.getElementById('chatMessageInput');
    if (input) {
        input.value = text;
        input.focus();
    }
    window.toggleQuickReplies();
};

// ============================================
// POLLING AUTOMÁTICO DE MENSAJES
// ============================================

function iniciarPollingMensajes(idTicket) {
    console.log('[Polling] Iniciando actualización automática para ticket #' + idTicket);
    
    // Limpiar intervalo anterior si existe
    detenerPollingMensajes();
    
    // Polling cada 3 segundos
    window.pollingInterval = setInterval(async function() {
        if (document.hidden) return;
        if (window.currentTicketId === idTicket) {
            try {
                await cargarMensajesTicket(idTicket);
            } catch (error) {
                console.error('[Polling] Error al actualizar mensajes:', error);
            }
        } else {
            // Si cambió el ticket, detener polling
            detenerPollingMensajes();
        }
    }, 3000);
}

function detenerPollingMensajes() {
    if (window.pollingInterval) {
        console.log('[Polling] Deteniendo actualización automática');
        clearInterval(window.pollingInterval);
        window.pollingInterval = null;
    }
}

// ============================================
// HELPERS
// ============================================

function formatearHora(fechaStr) {
    if (!fechaStr) return '';
    try {
        var fecha = new Date(fechaStr);
        return fecha.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '';
    }
}

// ============================================
// EVENT LISTENERS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    var chatInputDesktop = document.getElementById('chatMessageInputDesktop');
    var chatInputMobile = document.getElementById('chatMessageInput');
    
    if (chatInputDesktop) {
        chatInputDesktop.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                window.enviarMensaje();
            }
        });
    }
    
    if (chatInputMobile) {
        chatInputMobile.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                window.enviarMensaje();
            }
        });
    }
});

// Detener polling al cambiar de pestaña o cerrar página
window.addEventListener('beforeunload', function() {
    detenerPollingMensajes();
});

document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Pausar polling cuando la pestaña no está visible
        detenerPollingMensajes();
    } else {
        // Reanudar si hay un ticket activo
        if (window.currentTicketId && !window.pollingInterval) {
            iniciarPollingMensajes(window.currentTicketId);
        }
    }
});

// Función para enviar desde botón desktop
window.sendChatMessageDesktop = function() {
    window.enviarMensaje();
};

// Función para enviar desde botón mobile
window.sendChatMessage = function() {
    window.enviarMensaje();
};

console.log('✅ ticket-chat.js cargado correctamente');
