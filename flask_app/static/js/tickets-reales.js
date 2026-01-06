/**
 * Script para cargar tickets REALES desde la API
 * Reemplaza los datos hardcodeados del dashboard
 */

// COLORES ESTANDARIZADOS DEL SISTEMA
window.COLORES_PRIORIDAD = {
    1: { badge: 'bg-danger', text: 'Urgente', hex: '#dc3545' },
    2: { badge: 'bg-warning text-dark', text: 'Alta', hex: '#ffc107' },
    3: { badge: 'bg-primary', text: 'Media', hex: '#0d6efd' },
    4: { badge: 'bg-secondary', text: 'Baja', hex: '#6c757d' }
};

window.COLORES_ESTADO = {
    1: { badge: 'bg-info', text: 'Nuevo', hex: '#0dcaf0' },
    2: { badge: 'bg-primary', text: 'En Proceso', hex: '#0d6efd' },
    3: { badge: 'bg-success', text: 'Resuelto', hex: '#198754' },
    4: { badge: 'bg-secondary', text: 'Cerrado', hex: '#6c757d' },
    5: { badge: 'bg-warning text-dark', text: 'Pendiente', hex: '#ffc107' },
    6: { badge: 'bg-danger', text: 'Sin responder', hex: '#dc3545' }
};

// Base URL de la API
const API_BASE_URL = '/api';

// ============================================
// FUNCIÓN PRINCIPAL: Cargar Tickets Reales
// ============================================

async function cargarTicketsReales() {
    try {
        console.log('🎫 Cargando tickets reales desde API...');
        
        const apiUrl = `/tickets?limit=50&offset=0`;
        console.log('📡 Llamando a:', apiUrl);
        
        // Usar apiRequest de auth.js que incluye headers de autenticación
        const data = await apiRequest(apiUrl);
        
        console.log('✅ JSON parseado:', data);
        
        if (!data.success) {
            console.error('❌ Error en respuesta:', data.error || data.mensaje);
            mostrarErrorCarga();
            return;
        }
        
        console.log(`✅ ${data.tickets.length} tickets cargados de ${data.total} totales`);

        // Asegurar que el filtro de receptor incluya a todos los owners presentes en la lista,
        // aunque el endpoint /tickets/receptores no los traiga (por permisos/depto).
        try {
            actualizarFiltroReceptoresDesdeTickets(data.tickets);
        } catch (e) {
            console.warn('⚠️ No se pudo actualizar filtro Receptor desde tickets:', e);
        }
        
        // Renderizar tickets en el contenedor
        renderizarTicketsEnLista(data.tickets);
        
        // Actualizar KPIs si existen
        actualizarKPIsConTickets(data.tickets, data.total);
        
    } catch (error) {
        console.error('❌ Error al conectar con la API:', error);
        console.error('Detalles del error:', {
            message: error.message,
            stack: error.stack
        });
        mostrarErrorCarga();
    }
}

// ============================================
// FILTRO RECEPTOR: COMPLETAR DESDE TICKETS
// ============================================

function actualizarFiltroReceptoresDesdeTickets(tickets) {
    const selectOperador = document.getElementById('operatorFilter');
    if (!selectOperador || !Array.isArray(tickets)) return;

    // Indexar opciones existentes
    const existing = new Set();
    Array.from(selectOperador.options || []).forEach(opt => {
        existing.add(String(opt.value));
    });

    // Asegurar opciones base si por alguna razón no existen
    if (!existing.has('')) {
        const optAll = document.createElement('option');
        optAll.value = '';
        optAll.textContent = 'Todos';
        selectOperador.insertBefore(optAll, selectOperador.firstChild);
        existing.add('');
    }
    if (!existing.has('__unassigned__')) {
        const optUnassigned = document.createElement('option');
        optUnassigned.value = '__unassigned__';
        optUnassigned.textContent = 'Sin asignar';
        // Insertar después de "Todos"
        const afterAll = selectOperador.querySelector('option[value=""]');
        if (afterAll && afterAll.nextSibling) {
            selectOperador.insertBefore(optUnassigned, afterAll.nextSibling);
        } else {
            selectOperador.appendChild(optUnassigned);
        }
        existing.add('__unassigned__');
    }

    // Agregar owners presentes en tickets
    tickets.forEach(t => {
        const idOperador = t?.id_operador;
        const nombre = t?.operador_nombre;
        if (!idOperador || !nombre) return;

        const key = String(idOperador);
        if (existing.has(key)) return;

        const option = document.createElement('option');
        option.value = key;
        option.textContent = nombre;
        selectOperador.appendChild(option);
        existing.add(key);
    });
}

// ============================================
// RENDERIZAR TICKETS EN LA LISTA
// ============================================

function renderizarTicketsEnLista(tickets) {
    const contenedor = document.getElementById('ticketsScrollContainer');
    
    if (!contenedor) {
        console.warn('⚠️ Contenedor de tickets no encontrado');
        return;
    }
    
    // Limpiar contenedor
    contenedor.innerHTML = '';
    
    if (!tickets || tickets.length === 0) {
        contenedor.innerHTML = `
            <div class="empty-state text-center py-5">
                <i class="bi bi-inbox fs-1 text-muted d-block mb-3"></i>
                <h5 class="text-muted">No hay tickets disponibles</h5>
                <p class="text-muted">Los tickets aparecerán aquí cuando se creen.</p>
            </div>
        `;
        return;
    }
    
    // Renderizar cada ticket
    tickets.forEach((ticket, index) => {
        const ticketCard = crearTarjetaTicket(ticket);
        contenedor.appendChild(ticketCard);
    });
    
    console.log(`✅ ${tickets.length} tickets renderizados`);
}

// ============================================
// CREAR TARJETA DE TICKET
// ============================================

function crearTarjetaTicket(ticket) {
    const div = document.createElement('div');
    div.className = 'ticket-card';
    div.setAttribute('data-ticket-id', ticket.id_ticket);
    div.setAttribute('data-status', mapearEstado(ticket.estado));
    div.setAttribute('data-prioridad', ticket.id_prioridad);  // Para filtros de prioridad
    div.setAttribute('data-operador-id', ticket.id_operador || '');  // ID del operador asignado (receptor)
    div.setAttribute('data-remitente-id', ticket.id_operador_emisor || '');  // ID del operador que creó el ticket (emisor)
    div.setAttribute('data-depto-id', ticket.id_depto || '');  // ID del departamento del ticket
    div.setAttribute('data-depto-owner-id', ticket.id_depto_owner || '');  // Fallback: depto del Owner (tickets antiguos)

    const idUsuarioActual = window.perfilUsuario?.id_operador ?? window.perfilUsuario?.operador_id ?? window.perfilUsuario?.id;
    const esMio = !!idUsuarioActual && String(ticket.id_operador_emisor) === String(idUsuarioActual);
    const sinAsignar = !ticket.id_operador;
    const sinAsignarMio = sinAsignar && esMio;

    const puedeTomar = (() => {
        const deptos = window.perfilUsuario?.departamentos;
        if (!Array.isArray(deptos) || deptos.length === 0) return false;
        const deptoTicket = ticket.id_depto || ticket.id_depto_owner;
        if (!deptoTicket) return false;
        return deptos.some(d => String(d.id_depto || d.id_departamento) === String(deptoTicket));
    })();

    const porTomar = sinAsignar && !esMio && puedeTomar;

    if (porTomar) {
        div.classList.add('ticket-card-por-tomar');
    }

    if (sinAsignarMio) {
        div.style.opacity = '0.6';
        div.style.cursor = 'not-allowed';
        div.onclick = (e) => {
            e?.preventDefault?.();
            if (typeof showToast === 'function') {
                showToast('Esperando atención: un agente del departamento debe tomar el ticket', 'info');
            }
        };
    } else {
        div.onclick = () => seleccionarTicket(ticket.id_ticket);
    }
    
    // Calcular tiempo desde creación
    const tiempoCreacion = calcularTiempoTranscurrido(ticket.fecha_ini);
    
    // Mapear prioridad y estado a clases CSS
    const claseEstado = obtenerClaseEstado(ticket.id_estado);
    const clasePrioridad = obtenerClasePrioridad(ticket.id_prioridad);
    const iconoCanal = obtenerIconoCanal(ticket.id_canal || 1);
    
    const nombreHeader = (() => {
        // Regla clave:
        // - Si el ticket está SIN asignar y lo creó el usuario actual: no mostrar su propio nombre.
        //   Debe verse como "Sin operador" + badge "Esperando atención".
        if (sinAsignarMio) return 'Sin operador';

        // Si está sin asignar (no es mío), es útil mostrar quién lo emitió.
        if (sinAsignar) return ticket.emisor_nombre || ticket.usuario_nombre || (ticket.usuario && ticket.usuario.nombre) || 'Sin operador';

        // Si está asignado, priorizar el operador asignado.
        return ticket.operador_nombre || ticket.usuario_nombre || (ticket.usuario && ticket.usuario.nombre) || ticket.emisor_nombre || 'Operador';
    })();

    const estadoHeader = sinAsignarMio
        ? '<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split"></i> Esperando atención</span>'
        : '';

    const badgeEstadoFooter = porTomar
        ? '<span class="badge bg-info text-white"><i class="bi bi-hand-thumbs-up"></i> Por tomar</span>'
        : `<span class="badge ${claseEstado}">${ticket.estado || 'Sin estado'}</span>`;

    const safeTitulo = (ticket.titulo || '').replace(/'/g, "\\'");
    const btnTomar = porTomar
        ? `<button class="btn btn-sm btn-success" onclick="event.stopPropagation(); if (window.mostrarModalTomarTicket) window.mostrarModalTomarTicket(${ticket.id_ticket}, '${safeTitulo}')" title="Tomar ticket">
                <i class="bi bi-hand-thumbs-up"></i>
           </button>`
        : '';

    div.innerHTML = `
        <div class="ticket-card-meta">
            <div class="ticket-card-user">
                <div class="ticket-card-user-avatar">
                    <i class="bi bi-person-fill"></i>
                </div>
                <span class="ticket-card-user-name">${nombreHeader}</span>
            </div>
            <div class="ticket-card-meta-right">
                <span class="ticket-agent-response responded">
                    <i class="bi bi-clock"></i> ${tiempoCreacion}
                </span>
                ${estadoHeader}
            </div>
        </div>
        
        <div class="ticket-card-header">
            <span class="ticket-card-id">#${ticket.id_ticket}</span>
            ${iconoCanal}
        </div>
        
        <div class="ticket-card-subject">${ticket.titulo || 'Sin título'}</div>
        
        <div class="ticket-card-preview">
            ${ticket.descripcion ? truncarTexto(ticket.descripcion, 120) : 'Sin descripción'}
        </div>
        
        <div class="ticket-card-dates">
            <div class="ticket-date-item">
                <i class="bi bi-calendar-plus"></i>
                <span>Creado: ${formatearFechaCompleta(ticket.fecha_ini)}</span>
            </div>
        </div>
        
        <div class="ticket-card-footer">
            <div class="ticket-card-badges">
                ${badgeEstadoFooter}
                <span class="badge ${clasePrioridad}">${ticket.prioridad || 'Sin prioridad'}</span>
            </div>
            <div class="d-flex align-items-center gap-2">
                ${btnTomar}
                ${ticket.mensajes && ticket.mensajes.length > 0 ? `<span class="ticket-card-unread">${ticket.mensajes.length}</span>` : ''}
            </div>
        </div>
    `;
    
    return div;
}

// ============================================
// FUNCIONES AUXILIARES: MAPEO Y FORMATO
// ============================================

function mapearEstado(estado) {
    if (!estado) return 'pendiente';
    const e = String(estado).toLowerCase().replace(/\s+/g, ' ').trim();
    if (e === 'nuevo') return 'pendiente';
    if (e === 'pendiente') return 'pendiente';
    if (e === 'en proceso') return 'en-proceso';
    if (e === 'en progreso') return 'en-proceso';
    if (e === 'resuelto') return 'resuelto';
    if (e === 'cerrado') return 'cerrado';
    if (e === 'sin responder') return 'sin-respuesta';
    if (e === 'sin respuesta') return 'sin-respuesta';
    if (e === 'rechazado') return 'rechazado';
    return 'pendiente';
}

function obtenerClaseEstado(idEstado) {
    // Alinear con los IDs reales del sistema (ver window.COLORES_ESTADO)
    const clases = {
        1: 'bg-info text-white',            // Nuevo
        2: 'bg-primary text-white',         // En Proceso
        3: 'bg-success text-white',         // Resuelto
        4: 'bg-secondary text-white',       // Cerrado
        5: 'bg-warning text-dark',          // Pendiente
        6: 'bg-danger text-white'           // Sin responder
    };
    return clases[idEstado] || 'bg-secondary text-white';
}

function obtenerClasePrioridad(idPrioridad) {
    // Alinear con window.COLORES_PRIORIDAD (1 Urgente, 2 Alta, 3 Media, 4 Baja)
    const clases = {
        1: 'bg-danger text-white',
        2: 'bg-warning text-dark',
        3: 'bg-primary text-white',
        4: 'bg-secondary text-white'
    };
    return clases[idPrioridad] || 'bg-secondary text-white';
}

function obtenerIconoCanal(idCanal) {
    const iconos = {
        1: '<i class="bi bi-envelope-fill text-primary ms-auto" style="font-size: 0.9rem;" title="Email"></i>',
        2: '<i class="bi bi-chat-dots-fill text-info ms-auto" style="font-size: 0.9rem;" title="Chat"></i>',
        3: '<i class="bi bi-telephone-fill text-warning ms-auto" style="font-size: 0.9rem;" title="Teléfono"></i>',
        4: '<i class="bi bi-laptop-fill text-success ms-auto" style="font-size: 0.9rem;" title="Sistema"></i>',
        5: '<i class="bi bi-whatsapp text-success ms-auto" style="font-size: 0.9rem;" title="WhatsApp"></i>'
    };
    return iconos[idCanal] || iconos[1];
}

function calcularTiempoTranscurrido(fechaStr) {
    if (!fechaStr) return 'Fecha desconocida';
    
    const fecha = new Date(fechaStr);
    const ahora = new Date();
    const diferencia = Math.floor((ahora - fecha) / 1000); // segundos
    
    if (diferencia < 60) return 'Hace menos de 1 min';
    if (diferencia < 3600) return `Hace ${Math.floor(diferencia / 60)} min`;
    if (diferencia < 86400) return `Hace ${Math.floor(diferencia / 3600)}h`;
    if (diferencia < 2592000) return `Hace ${Math.floor(diferencia / 86400)}d`;
    
    return formatearFechaCompleta(fechaStr);
}

function formatearFechaCompleta(fechaStr) {
    if (!fechaStr) return 'N/A';
    
    const fecha = new Date(fechaStr);
    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const anio = fecha.getFullYear();
    const hora = String(fecha.getHours()).padStart(2, '0');
    const minutos = String(fecha.getMinutes()).padStart(2, '0');
    
    return `${dia}/${mes}/${anio} ${hora}:${minutos}`;
}

function truncarTexto(texto, maxLength) {
    if (!texto) return '';
    if (texto.length <= maxLength) return texto;
    return texto.substring(0, maxLength) + '...';
}

// ============================================
// SELECCIONAR Y VER TICKET
// ============================================

async function seleccionarTicket(idTicket) {
    try {
        console.log(`📋 Cargando detalle del ticket #${idTicket}...`);
        
        // Marcar ticket como seleccionado visualmente
        const todosLosTickets = document.querySelectorAll('.ticket-item');
        todosLosTickets.forEach(item => item.classList.remove('selected'));
        
        const ticketElement = document.querySelector(`.ticket-item[data-ticket-id="${idTicket}"]`);
        if (ticketElement) {
            ticketElement.classList.add('selected');
        }
        
        // Usar apiRequest de auth.js que incluye headers de autenticación
        const data = await apiRequest(`/tickets/${idTicket}`);
        
        console.log('📨 Respuesta recibida:', data);
        
        if (!data.success) {
            console.error('❌ Error al cargar ticket:', data.error || data.mensaje);
            alert('Error al cargar el ticket. Por favor, intente nuevamente.');
            return;
        }
        
        const ticket = data.data || data.ticket;
        console.log('✅ Ticket cargado:', ticket);
        
        // Establecer el ticket actual y mostrar el detalle
        mostrarDetalleTicket(ticket);
        
    } catch (error) {
        console.error('❌ Error al cargar ticket:', error);
        console.error('Detalles:', error.message);
        alert('Error de conexión. Por favor, intente nuevamente.');
    }
}

function mostrarDetalleTicket(ticket) {
    // IMPORTANTE: Limpiar mensajes del ticket anterior
    window.chatMessages = [];
    
    // Establecer el ticket actual para el chat
    window.currentTicketId = ticket.id_ticket;
    
    console.log('🎫 Mostrando detalle:', ticket);
    console.log('✅ currentTicketId establecido a:', window.currentTicketId);
    console.log('🧹 Mensajes anteriores limpiados');

    // Bloquear/permitir envío de mensajes según si el ticket fue tomado
    actualizarPermisosChat(ticket);

    // Reiniciar polling de mensajes para el ticket seleccionado
    if (typeof detenerPollingMensajes === 'function') {
        detenerPollingMensajes();
    }
    
    // Actualizar mensajes del ticket si existen
    if (ticket.mensajes && ticket.mensajes.length > 0) {
        console.log(`💬 ${ticket.mensajes.length} mensajes en este ticket`);
    }
    
    // ===== ACTUALIZAR PANEL DE INFORMACIÓN DEL TICKET =====
    actualizarPanelInformacion(ticket);
    
    // ===== CARGAR HISTORIAL DEL TICKET =====
    cargarHistorialTicket(window.currentTicketId);
    
    // Abrir el panel de chat en desktop
    if (typeof selectTicketDesktop === 'function') {
        selectTicketDesktop(ticket.id_ticket, null);
        console.log('✅ Panel de chat abierto');

    } else {
        console.warn('⚠️ Función selectTicketDesktop no disponible');
    }
    
    // CARGAR MENSAJES DEL TICKET INMEDIATAMENTE
    if (typeof cargarMensajesTicket === 'function') {
        cargarMensajesTicket(window.currentTicketId);
        console.log('✅ Cargando mensajes del ticket');

        if (typeof iniciarPollingMensajes === 'function') {
            iniciarPollingMensajes(window.currentTicketId);
        }
    } else {
        console.warn('⚠️ Función cargarMensajesTicket no disponible');
    }
}

function actualizarPermisosChat(ticket) {
    const inputDesktop = document.getElementById('chatMessageInputDesktop');
    const inputMobile = document.getElementById('chatMessageInput');

    const btnDesktop = inputDesktop ? inputDesktop.nextElementSibling : null;
    const btnMobile = inputMobile ? inputMobile.nextElementSibling : null;

    const currentUser = (typeof AuthService !== 'undefined' && AuthService.getCurrentUser)
        ? AuthService.getCurrentUser()
        : null;
    const currentOperadorId = currentUser ? (currentUser.id_operador || currentUser.id) : null;

    const ownerIdRaw = (ticket && (ticket.id_operador_owner ?? ticket.id_operador ?? ticket.id_operador_asignado)) ?? null;
    const ownerId = ownerIdRaw !== null && ownerIdRaw !== undefined ? parseInt(ownerIdRaw, 10) : null;
    const sinAsignar = !ownerId;
    const noResponsable = !!(ownerId && currentOperadorId && ownerId !== parseInt(currentOperadorId, 10));
    const idEstado = ticket?.id_estado;
    const estadoTxt = String(ticket?.estado || ticket?.estado_desc || '').toLowerCase().trim();
    const cerrado = (String(idEstado) === '4') || (estadoTxt === 'cerrado');

    window.chatBloqueadoPorNoTomado = !!sinAsignar;
    window.chatBloqueadoPorNoResponsable = !!noResponsable;
    window.chatBloqueadoPorCerrado = !!cerrado;

    const placeholderDisabledNoTomado = 'Debes tomar el ticket para responder...';
    const placeholderDisabledNoResponsable = 'Solo el responsable del ticket puede responder.';
    const placeholderDisabledCerrado = 'Ticket cerrado: no se puede responder.';
    const placeholderEnabled = 'Escribe un mensaje...';

    const setEnabled = (inputEl, btnEl, enabled) => {
        if (inputEl) {
            inputEl.disabled = !enabled;
            inputEl.placeholder = enabled ? placeholderEnabled : placeholderDisabled;
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

    const enabled = !sinAsignar && !noResponsable && !cerrado;
    const placeholder = cerrado
        ? placeholderDisabledCerrado
        : (sinAsignar
            ? placeholderDisabledNoTomado
            : (noResponsable ? placeholderDisabledNoResponsable : placeholderEnabled));

    const setEnabledWithPlaceholder = (inputEl, btnEl) => {
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

    setEnabledWithPlaceholder(inputDesktop, btnDesktop);
    setEnabledWithPlaceholder(inputMobile, btnMobile);
}

// ============================================
// ACTUALIZAR KPIs
// ============================================

function actualizarKPIsConTickets(tickets, total) {
    // Calcular estadísticas
    const ticketsAbiertos = tickets.filter(t => 
        ['Nuevo', 'En Proceso'].includes(t.estado)
    ).length;
    
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const nuevosHoy = tickets.filter(t => {
        const fechaTicket = new Date(t.fecha_ini);
        fechaTicket.setHours(0, 0, 0, 0);
        return fechaTicket.getTime() === hoy.getTime();
    }).length;
    
    // Actualizar DOM
    const kpiAbiertos = document.getElementById('kpi-tickets-abiertos');
    const kpiNuevosHoy = document.getElementById('kpi-nuevos-hoy');
    const kpiMisTickets = document.getElementById('kpi-mis-tickets');
    
    if (kpiAbiertos) kpiAbiertos.textContent = ticketsAbiertos;
    if (kpiNuevosHoy) kpiNuevosHoy.textContent = nuevosHoy;
    if (kpiMisTickets) kpiMisTickets.textContent = total;
    
    console.log(`📊 KPIs actualizados: ${ticketsAbiertos} abiertos, ${nuevosHoy} nuevos hoy, ${total} totales`);
}

// ============================================
// MANEJO DE ERRORES
// ============================================

function mostrarErrorCarga() {
    const contenedor = document.getElementById('ticketsScrollContainer');
    
    if (contenedor) {
        contenedor.innerHTML = `
            <div class="alert alert-danger m-3" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>Error al cargar tickets</strong>
                <p class="mb-2">No se pudieron cargar los tickets desde el servidor.</p>
                <button class="btn btn-sm btn-outline-danger" onclick="cargarTicketsReales()">
                    <i class="bi bi-arrow-clockwise me-1"></i> Reintentar
                </button>
            </div>
        `;
    }
}

// ============================================
// INICIALIZACIÓN
// ============================================

// Cargar tickets cuando se hace clic en la pestaña de Tickets
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Script de tickets reales cargado');
    
    // Cargar tickets inmediatamente (sin esperar evento de tab)
    setTimeout(() => {
        console.log('⏱️ Iniciando carga de tickets...');
        cargarTicketsReales();
        
        // También registrar evento de tab si existe
        const ticketTab = document.getElementById('ticket-tab');
        if (ticketTab) {
            ticketTab.addEventListener('shown.bs.tab', function() {
                console.log('📂 Pestaña de Tickets mostrada - Recargando datos...');
                cargarTicketsReales();
            });
        }
    }, 300);
});

// ============================================
// ACTUALIZAR PANEL DE INFORMACIÓN DEL TICKET
// ============================================

function actualizarPanelInformacion(ticket) {
    console.log('📋 Actualizando panel de información con:', ticket);
    
    // Mapeo de canales
    const canalesIconos = {
        'email': '<i class="bi bi-envelope-fill text-primary"></i>',
        'whatsapp': '<i class="bi bi-whatsapp text-success"></i>',
        'web': '<i class="bi bi-globe text-info"></i>',
        'telefono': '<i class="bi bi-telephone-fill text-warning"></i>'
    };
    
    // Usar colores estandarizados del sistema
    const estadosColores = window.COLORES_ESTADO;
    const prioridadesColores = window.COLORES_PRIORIDAD;
    
    // Formatear fecha
    const formatearFecha = (fecha) => {
        if (!fecha) return 'N/A';
        const date = new Date(fecha);
        return date.toLocaleString('es-CL', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };
    
    // Actualizar Ticket ID
    const ticketIdElem = document.querySelector('#ticketDetailsOffcanvas .fw-bold.text-brand-blue');
    if (ticketIdElem) {
        ticketIdElem.textContent = `#${ticket.id_ticket}`;
    }
    
    // Actualizar Canal
    const canalElem = document.querySelector('#ticketDetailsOffcanvas .d-flex.align-items-center.gap-1');
    if (canalElem && ticket.canal) {
        const canalNombre = ticket.canal.charAt(0).toUpperCase() + ticket.canal.slice(1);
        canalElem.innerHTML = `
            ${canalesIconos[ticket.canal] || '<i class="bi bi-question-circle"></i>'}
            <span class="small">${canalNombre}</span>
        `;
    }
    
    // Actualizar Estado
    const estadoContainer = document.querySelectorAll('#ticketDetailsOffcanvas .d-flex.justify-content-between.align-items-center')[2];
    if (estadoContainer && ticket.id_estado) {
        const estadoBadge = estadoContainer.querySelector('span:last-child');
        if (estadoBadge) {
            const colorEstado = estadosColores[ticket.id_estado];
            estadoBadge.className = `badge ${colorEstado ? colorEstado.badge : 'bg-secondary'}`;
            estadoBadge.textContent = colorEstado ? colorEstado.text : ticket.estado;
        }
    }
    
    // Actualizar Prioridad
    const prioridadContainer = document.querySelectorAll('#ticketDetailsOffcanvas .d-flex.justify-content-between.align-items-center')[3];
    if (prioridadContainer && ticket.id_prioridad) {
        const prioridadBadge = prioridadContainer.querySelector('span:last-child');
        if (prioridadBadge) {
            const colorPrioridad = prioridadesColores[ticket.id_prioridad];
            prioridadBadge.className = `badge ${colorPrioridad ? colorPrioridad.badge : 'bg-secondary'}`;
            prioridadBadge.textContent = colorPrioridad ? colorPrioridad.text : ticket.prioridad;
        }
    }
    
    // Actualizar Fecha de Creación
    const fechaContainer = document.querySelectorAll('#ticketDetailsOffcanvas .d-flex.justify-content-between.align-items-center')[4];
    if (fechaContainer && ticket.fecha_ini) {
        const fechaElem = fechaContainer.querySelector('span:last-child');
        if (fechaElem) {
            fechaElem.textContent = formatearFecha(ticket.fecha_ini);
        }
    }
    
    // Actualizar Asunto
    const asuntoElem = document.querySelector('#ticketDetailsOffcanvas div > p.mb-0');
    if (asuntoElem && ticket.asunto) {
        asuntoElem.textContent = ticket.asunto;
    }
    
    // Actualizar Usuario Solicitante
    const usuarioNombreElem = document.querySelector('#ticketDetailsOffcanvas .participant-list .fw-semibold');
    if (usuarioNombreElem && ticket.usuario_nombre) {
        usuarioNombreElem.textContent = ticket.usuario_nombre;
    }
    
    // Actualizar información del Emisor y Owner
    actualizarEmisorYOwner(ticket);
    
    // Ocultar secciones sin datos reales
    ocultarSeccionesTemporales();
}

function actualizarEmisorYOwner(ticket) {
    console.log('👤 Actualizando Emisor y Owner:', {
        emisor_id: ticket.id_operador_emisor,
        emisor_nombre: ticket.emisor_nombre,
        owner_id: ticket.id_operador,
        operador_nombre: ticket.operador_nombre,
        operador_aceptado: ticket.operador_aceptado
    });
    
    // Obtener la sección "Equipo de Soporte"
    const equipoSoporteSection = document.querySelector('#ticketDetailsOffcanvas .p-4.border-bottom:nth-child(2)');
    if (!equipoSoporteSection) return;
    
    // Mostrar la sección
    equipoSoporteSection.style.display = 'block';
    
    // Actualizar el título
    const tituloEquipo = equipoSoporteSection.querySelector('h6');
    if (tituloEquipo) {
        tituloEquipo.innerHTML = '<i class="bi bi-people-fill me-2"></i>Participantes del Ticket';
    }
    
    // Ocultar botón "Agregar"
    const btnAgregar = equipoSoporteSection.querySelector('button');
    if (btnAgregar) {
        btnAgregar.style.display = 'none';
    }
    
    // Limpiar lista de participantes
    const participantList = equipoSoporteSection.querySelector('.participant-list');
    if (!participantList) return;
    
    participantList.innerHTML = '';
    
    // 1. EMISOR DEL TICKET (quien lo creó)
    if (ticket.emisor_nombre || ticket.id_operador_emisor) {
        const nombreEmisor = ticket.emisor_nombre || `Operador #${ticket.id_operador_emisor}`;
        const emisorHTML = `
            <div class="participant-item" style="background: rgba(25, 135, 84, 0.05); border-left: 3px solid #198754; padding: 10px; border-radius: 8px; margin-bottom: 12px;">
                <div class="participant-avatar" style="background: linear-gradient(135deg, #198754, #20c997); color: white;">
                    <i class="bi bi-pencil-square"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="fw-semibold">${nombreEmisor}</div>
                    <small class="text-success"><i class="bi bi-person-plus-fill me-1"></i>Emisor del Ticket</small>
                </div>
            </div>
        `;
        participantList.insertAdjacentHTML('beforeend', emisorHTML);
    }
    
    // 2. OPERADOR ASIGNADO (Owner actual del ticket)
        if (ticket.id_operador && ticket.operador_nombre) {
            // En el flujo actual, si está asignado (incluye "Tomar"), se considera activo.
            const ownerHTML = `
                <div class="participant-item" style="background: rgba(13, 110, 253, 0.05); border-left: 3px solid #0d6efd; padding: 10px; border-radius: 8px;">
                    <div class="participant-avatar" style="background: linear-gradient(135deg, #0d6efd, #0dcaf0); color: white;">
                        <i class="bi bi-person-check-fill"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-semibold">${ticket.operador_nombre}</div>
                        <small class="text-primary"><i class="bi bi-shield-check me-1"></i>Asignado / Responsable</small>
                    </div>
                    <span class="badge bg-primary">Activo</span>
                </div>
            `;
            participantList.insertAdjacentHTML('beforeend', ownerHTML);
        } else {
        // Si no hay owner, mostrar mensaje
        const sinOwnerHTML = `
            <div class="participant-item" style="background: rgba(255, 193, 7, 0.05); border-left: 3px solid #ffc107; padding: 10px; border-radius: 8px;">
                <div class="participant-avatar" style="background: #ffc107; color: #000;">
                    <i class="bi bi-hourglass-split"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="fw-semibold">Sin asignar</div>
                    <small class="text-warning"><i class="bi bi-exclamation-circle me-1"></i>Ticket pendiente de asignación</small>
                </div>
                <span class="badge bg-warning text-dark">Disponible</span>
            </div>
        `;
        participantList.insertAdjacentHTML('beforeend', sinOwnerHTML);
    }
}

function ocultarSeccionesTemporales() {
    // NO ocultar "Equipo de Soporte" - ahora muestra Emisor y Owner
    // La sección ahora se muestra con actualizarEmisorYOwner()
    
    // Ocultar "Usuarios Involucrados" (además del solicitante)
    const usuariosSection = document.querySelectorAll('#ticketDetailsOffcanvas .p-4.border-bottom')[2];
    if (usuariosSection) {
        // Ocultar solo los usuarios adicionales, dejar el principal
        const participantItems = usuariosSection.querySelectorAll('.participant-item');
        participantItems.forEach((item, index) => {
            if (index > 0) {
                item.style.display = 'none';
            }
        });
    }
    
    // Ocultar "Archivos Adjuntos" temporalmente
    const adjuntosSection = document.querySelectorAll('#ticketDetailsOffcanvas .p-4.border-bottom')[3];
    if (adjuntosSection) {
        adjuntosSection.style.display = 'none';
    }
}

// ============================================
// CARGAR HISTORIAL DEL TICKET
// ============================================

async function cargarHistorialTicket(idTicket) {
    try {
        console.log(`📜 Cargando historial del ticket #${idTicket}...`);
        
        const data = await apiRequest(`/tickets/${idTicket}/historial`);
        
        if (!data.success) {
            console.error('❌ Error al cargar historial:', data.error);
            return;
        }
        
        const historial = data.data || [];
        console.log(`✅ ${historial.length} eventos en el historial`);
        
        mostrarHistorialEnPanel(historial);
        
    } catch (error) {
        console.error('❌ Error al cargar historial:', error);
    }
}

function mostrarHistorialEnPanel(historial) {
    const timelineContainer = document.querySelector('.ticket-activity-timeline');
    if (!timelineContainer) {
        console.warn('⚠️ Contenedor de historial no encontrado');
        return;
    }
    
    // Limpiar historial anterior
    timelineContainer.innerHTML = '';
    
    if (historial.length === 0) {
        timelineContainer.innerHTML = '<p class="text-muted small">No hay actividad registrada.</p>';
        return;
    }
    
    // Mapeo de acciones a iconos
    const accionesIconos = {
        'Creación': '<i class="bi bi-plus-circle-fill"></i>',
        'Cambio de estado': '<i class="bi bi-arrow-repeat"></i>',
        'Cambio de prioridad': '<i class="bi bi-flag-fill"></i>',
        'Asignación': '<i class="bi bi-person-fill-add"></i>',
        'Respuesta': '<i class="bi bi-reply-fill"></i>',
        'Mensaje público': '<i class="bi bi-chat-dots-fill"></i>',
        'Mensaje privado': '<i class="bi bi-lock-fill"></i>',
        'Nota interna': '<i class="bi bi-pencil-square"></i>',
        'Etiqueta agregada': '<i class="bi bi-tag-fill"></i>'
    };
    
    // Mapeo de acciones a colores
    const accionesColores = {
        'Creación': 'bg-info',
        'Cambio de estado': 'bg-primary',
        'Cambio de prioridad': 'bg-warning',
        'Asignación': 'bg-success',
        'Respuesta': 'bg-success',
        'Mensaje público': 'bg-success',
        'Mensaje privado': 'bg-secondary',
        'Nota interna': 'bg-secondary',
        'Etiqueta agregada': 'bg-info'
    };
    
    // Función para calcular "hace X tiempo"
    const tiempoRelativo = (fecha) => {
        const ahora = new Date();
        const fechaEvento = new Date(fecha);
        const diff = Math.floor((ahora - fechaEvento) / 1000); // segundos
        
        if (diff < 60) return 'Hace unos segundos';
        if (diff < 3600) return `Hace ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} horas`;
        if (diff < 604800) return `Hace ${Math.floor(diff / 86400)} días`;
        return fechaEvento.toLocaleDateString('es-CL');
    };
    
    // Generar HTML para cada evento
    historial.forEach(evento => {
        const icono = accionesIconos[evento.accion] || '<i class="bi bi-circle-fill"></i>';
        const color = accionesColores[evento.accion] || 'bg-secondary';
        
        let descripcion = evento.accion;
        if (evento.valor_anterior && evento.valor_nuevo) {
            descripcion += `: ${evento.valor_anterior} → ${evento.valor_nuevo}`;
        } else if (evento.valor_nuevo) {
            descripcion += `: ${evento.valor_nuevo}`;
        }
        
        const itemHTML = `
            <div class="activity-item">
                <div class="activity-icon ${color}">
                    ${icono}
                </div>
                <div class="activity-content">
                    <div class="activity-header">
                        <strong>${evento.realizado_por}</strong> ${descripcion.toLowerCase()}
                    </div>
                    <div class="activity-time">${tiempoRelativo(evento.fecha)}</div>
                </div>
            </div>
        `;
        
        timelineContainer.insertAdjacentHTML('beforeend', itemHTML);
    });
}


// Exportar funciones para uso global
window.cargarTicketsReales = cargarTicketsReales;
window.seleccionarTicket = seleccionarTicket;
window.actualizarKPIsConTickets = actualizarKPIsConTickets;

console.log('✅ Módulo de tickets reales listo');
