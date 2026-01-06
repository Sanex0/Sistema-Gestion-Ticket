/**
 * Funciones para cambiar estado y prioridad de tickets
 */

// Mapeo de IDs de estado
const ESTADOS = {
    'nuevo': 1,
    'en-proceso': 2,
    'resuelto': 3,
    'cerrado': 4,
    'pendiente': 5,
    'sin-responder': 6
};

// Mapeo de IDs de prioridad
const PRIORIDADES = {
    'urgente': 1,
    'alta': 2,
    'media': 3,
    'normal': 3,  // Alias para media
    'baja': 4
};

/**
 * Cambia el estado de un ticket
 */
window.changeTicketStatus = async function(estadoNombre) {
    if (!window.currentTicketId) {
        showToast('❌ No hay un ticket seleccionado', 'warning');
        return;
    }
    
    const estadoId = ESTADOS[estadoNombre];
    if (!estadoId) {
        showToast('❌ Estado inválido', 'warning');
        return;
    }
    
    try {
        console.log(`Cambiando estado del ticket #${window.currentTicketId} a: ${estadoNombre} (ID: ${estadoId})`);
        
        const result = await DashboardAPI.cambiarEstadoTicket(window.currentTicketId, estadoId);
        
        if (result.success) {
            showToast(`✅ ${result.message}`, 'success');
            
            // Recargar el ticket actual para ver el cambio
            if (typeof seleccionarTicket === 'function') {
                await seleccionarTicket(window.currentTicketId);
            }
            
            // Recargar la lista de tickets
            if (typeof cargarTicketsReales === 'function') {
                await cargarTicketsReales();
            }
        } else {
            showToast(`❌ ${result.error || 'Error al cambiar el estado'}`, 'error');
        }
    } catch (error) {
        console.error('Error al cambiar estado:', error);
        showToast(`❌ ${error.message || 'Error al cambiar el estado'}`, 'error');
    }
};

/**
 * Cambia la prioridad de un ticket
 */
window.changeTicketPriority = async function(prioridadNombre) {
    if (!window.currentTicketId) {
        showToast('❌ No hay un ticket seleccionado', 'warning');
        return;
    }
    
    const prioridadId = PRIORIDADES[prioridadNombre];
    if (!prioridadId) {
        showToast('❌ Prioridad inválida', 'warning');
        return;
    }
    
    try {
        console.log(`Cambiando prioridad del ticket #${window.currentTicketId} a: ${prioridadNombre} (ID: ${prioridadId})`);
        
        const result = await DashboardAPI.cambiarPrioridadTicket(window.currentTicketId, prioridadId);
        
        if (result.success) {
            showToast(`✅ ${result.message}`, 'success');
            
            // Recargar el ticket actual para ver el cambio
            if (typeof seleccionarTicket === 'function') {
                await seleccionarTicket(window.currentTicketId);
            }
            
            // Recargar la lista de tickets
            if (typeof cargarTicketsReales === 'function') {
                await cargarTicketsReales();
            }
        } else {
            showToast(`❌ ${result.error || 'Error al cambiar la prioridad'}`, 'error');
        }
    } catch (error) {
        console.error('Error al cambiar prioridad:', error);
        showToast(`❌ ${error.message || 'Error al cambiar la prioridad'}`, 'error');
    }
};

/**
 * Filtrar tickets por prioridad
 */
window.filtrarPorPrioridad = async function(prioridadNombre, botonElement) {
    console.log(`📊 Filtrando tickets por prioridad: ${prioridadNombre}`);
    
    // Gestionar estado activo de botones
    if (botonElement) {
        // Obtener todos los botones de prioridad
        const todosBotones = document.querySelectorAll('.priority-filter-btn');
        
        // Si el botón ya está activo, desactivar (mostrar todos)
        if (botonElement.classList.contains('active')) {
            botonElement.classList.remove('active');

            // Resetear prioridad global
            window.activePriorityId = null;
            
            // Aplicar todos los filtros
            if (typeof applyAllFilters === 'function') {
                applyAllFilters();
            }
            
            showToast('📊 Mostrando todos los tickets', 'info');
            return;
        }
        
        // Desactivar todos los botones
        todosBotones.forEach(btn => btn.classList.remove('active'));
        
        // Activar el botón seleccionado
        botonElement.classList.add('active');

        // Setear prioridad global por ID (usa el mismo mapeo del módulo)
        window.activePriorityId = PRIORIDADES[prioridadNombre] || null;
        
        // Aplicar todos los filtros
        if (typeof applyAllFilters === 'function') {
            applyAllFilters();
        }
        
        const nombrePrioridad = prioridadNombre.charAt(0).toUpperCase() + prioridadNombre.slice(1);
        showToast(`📊 Filtrando por prioridad ${nombrePrioridad}`, 'info');
    }
};

console.log('✅ Módulo de cambio de estado y prioridad cargado');
