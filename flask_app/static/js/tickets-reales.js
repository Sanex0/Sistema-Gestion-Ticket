/**
 * Script para cargar tickets REALES desde la API
 * Reemplaza los datos hardcodeados del dashboard
 */

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
    div.onclick = () => seleccionarTicket(ticket.id_ticket);
    
    // Calcular tiempo desde creación
    const tiempoCreacion = calcularTiempoTranscurrido(ticket.fecha_ini);
    
    // Mapear prioridad y estado a clases CSS
    const claseEstado = obtenerClaseEstado(ticket.id_estado);
    const clasePrioridad = obtenerClasePrioridad(ticket.id_prioridad);
    const iconoCanal = obtenerIconoCanal(ticket.id_canal || 1);
    
    div.innerHTML = `
        <div class="ticket-card-meta">
            <div class="ticket-card-user">
                <div class="ticket-card-user-avatar">
                    <i class="bi bi-person-fill"></i>
                </div>
                <span class="ticket-card-user-name">${ticket.usuario?.nombre || 'Usuario Desconocido'}</span>
            </div>
            <span class="ticket-agent-response responded">
                <i class="bi bi-clock"></i> ${tiempoCreacion}
            </span>
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
                <span class="badge ${claseEstado}">${ticket.estado || 'Sin estado'}</span>
                <span class="badge ${clasePrioridad}">${ticket.prioridad || 'Sin prioridad'}</span>
            </div>
            ${ticket.mensajes && ticket.mensajes.length > 0 ? `<span class="ticket-card-unread">${ticket.mensajes.length}</span>` : ''}
        </div>
    `;
    
    return div;
}

// ============================================
// FUNCIONES AUXILIARES: MAPEO Y FORMATO
// ============================================

function mapearEstado(estado) {
    const mapa = {
        'Nuevo': 'pendiente',
        'En Proceso': 'en proceso',
        'Resuelto': 'resuelto',
        'Cerrado': 'cerrado',
        'Rechazado': 'rechazado'
    };
    return mapa[estado] || 'pendiente';
}

function obtenerClaseEstado(idEstado) {
    const clases = {
        1: 'bg-warning text-dark',    // Nuevo
        2: 'bg-info text-white',       // En Proceso
        3: 'bg-success text-white',    // Resuelto
        4: 'bg-secondary text-white',  // En Espera
        5: 'bg-danger text-white',     // Rechazado
        6: 'bg-dark text-white'        // Cerrado
    };
    return clases[idEstado] || 'bg-secondary text-white';
}

function obtenerClasePrioridad(idPrioridad) {
    const clases = {
        1: 'bg-secondary',           // Baja
        2: 'bg-primary',             // Media/Normal
        3: 'bg-danger',              // Alta
        4: 'prioridad-critica'       // Urgente/Crítica
    };
    return clases[idPrioridad] || 'bg-secondary';
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
    
    // Actualizar mensajes del ticket si existen
    if (ticket.mensajes && ticket.mensajes.length > 0) {
        console.log(`💬 ${ticket.mensajes.length} mensajes en este ticket`);
    }
    
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
    } else {
        console.warn('⚠️ Función cargarMensajesTicket no disponible');
    }
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


// Exportar funciones para uso global
window.cargarTicketsReales = cargarTicketsReales;
window.seleccionarTicket = seleccionarTicket;
window.actualizarKPIsConTickets = actualizarKPIsConTickets;

console.log('✅ Módulo de tickets reales listo');
