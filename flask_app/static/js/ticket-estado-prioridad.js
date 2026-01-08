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
    'urgente': 1,   // ID 1 = Urgente (Rojo)
    'alta': 2,      // ID 2 = Alta (Naranja)
    'media': 3,     // ID 3 = Media (Azul)
    'normal': 3,    // Alias para media
    'baja': 4       // ID 4 = Baja (Verde)
};

/**
 * Cambia el estado de un ticket
 */
window.changeTicketStatus = async function(estadoNombre) {
    if (!window.currentTicketId) {
        showToast('❌ No hay un ticket seleccionado', 'warning');
        return;
    }

    // Validación de permisos (alineado al backend)
    try {
        const ticket = window.currentTicket || null;
        const perms = window.getTicketStatusPermissions ? window.getTicketStatusPermissions(ticket) : null;
        if (ticket && perms && !perms.isAdmin) {
            const estadoActual = parseInt(ticket.id_estado ?? ticket.idEstado ?? 0, 10);
            const cerrado = estadoActual === 4;

            const allowed =
                (perms.canResolve && estadoNombre === 'resuelto') ||
                (perms.canClose && estadoNombre === 'cerrado') ||
                (perms.canReopen && cerrado && estadoNombre === 'en-proceso');

            if (!allowed) {
                showToast('❌ No tienes permisos para cambiar el estado a esa opción', 'warning');
                return;
            }
        }
    } catch (e) {
        console.warn('No se pudo validar permisos de estado:', e);
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

// ================================
// PERMISOS / UI PARA ESTADOS
// ================================

window.getTicketStatusPermissions = function(ticket) {
    const currentUser = (typeof AuthService !== 'undefined' && AuthService.getCurrentUser)
        ? AuthService.getCurrentUser()
        : null;

    const currentOperadorId = currentUser ? (currentUser.operador_id || currentUser.id_operador || currentUser.id) : null;
    const currentRol = currentUser ? (currentUser.rol || currentUser.rol_nombre || '') : '';
    const isAdmin = String(currentRol).toLowerCase().trim() === 'admin';

    const ownerIdRaw = ticket ? (ticket.id_operador_owner ?? ticket.id_operador ?? ticket.id_operador_asignado) : null;
    const emisorIdRaw = ticket ? ticket.id_operador_emisor : null;

    const ownerId = ownerIdRaw !== null && ownerIdRaw !== undefined ? parseInt(ownerIdRaw, 10) : null;
    const emisorId = emisorIdRaw !== null && emisorIdRaw !== undefined ? parseInt(emisorIdRaw, 10) : null;
    const currentIdInt = currentOperadorId !== null && currentOperadorId !== undefined ? parseInt(currentOperadorId, 10) : null;

    const esOwner = !!(ownerId && currentIdInt && ownerId === currentIdInt);
    const esEmisor = !!(emisorId && currentIdInt && emisorId === currentIdInt);
    const estadoActual = ticket ? parseInt(ticket.id_estado ?? ticket.idEstado ?? 0, 10) : 0;

    return {
        isAdmin,
        esOwner,
        esEmisor,
        canResolve: isAdmin || esOwner,
        canClose: isAdmin || esEmisor,
        canReopen: isAdmin || esEmisor,
        estadoActual,
        cerrado: estadoActual === 4
    };
};

window.updateTicketStatusUI = function(ticket) {
    const dropdowns = [
        document.getElementById('statusDropdown'),
        document.getElementById('statusDropdownMobile')
    ].filter(Boolean);

    const btns = [
        document.getElementById('statusActionBtn'),
        document.getElementById('statusActionBtnMobile')
    ].filter(Boolean);

    const perms = window.getTicketStatusPermissions(ticket);

    const allowedStates = (() => {
        if (perms.isAdmin) return ['pendiente', 'en-proceso', 'resuelto', 'cerrado'];
        // Receptor/Owner: solo Resuelto
        if (perms.esOwner && !perms.esEmisor) return ['resuelto'];
        // Emisor: solo Cerrado, y si está cerrado puede Reabrir -> En Proceso
        if (perms.esEmisor && !perms.esOwner) return perms.cerrado ? ['en-proceso'] : ['cerrado'];
        // Si es ambos (emisor y owner), permitir ambos flujos
        if (perms.esOwner && perms.esEmisor) {
            return perms.cerrado ? ['en-proceso', 'resuelto'] : ['cerrado', 'resuelto'];
        }
        return [];
    })();

    dropdowns.forEach(dd => {
        const items = Array.from(dd.querySelectorAll('[data-state]'));
        items.forEach(item => {
            const st = item.getAttribute('data-state');
            item.style.display = allowedStates.includes(st) ? '' : 'none';

            // Ajuste de label para reapertura (En Proceso)
            if (st === 'en-proceso') {
                const span = item.querySelector('span');
                const icon = item.querySelector('i');
                const debeMostrarseComoReabrir = perms.cerrado && perms.canReopen && !perms.canClose;
                if (span) span.textContent = debeMostrarseComoReabrir ? 'Reabrir' : 'En Proceso';
                if (icon) icon.className = debeMostrarseComoReabrir ? 'bi bi-arrow-counterclockwise' : 'bi bi-gear-fill';
            }
        });
    });

    // ================================
    // UX: Emisor = botón "Cerrar/Reabrir" (sin dropdown)
    //     Receptor/Owner = dropdown normal (si solo puede Resuelto, label "Resolver")
    // ================================
    const shouldBeDirectCloseButton = !!(perms.esEmisor && !perms.isAdmin && !perms.esOwner);
    const directState = shouldBeDirectCloseButton
        ? (allowedStates[0] || (perms.cerrado ? 'en-proceso' : 'cerrado'))
        : null;

    // Utilidad para setear label e ícono en botón desktop
    const setDesktopButtonContent = (label, iconClass) => {
        const btn = document.getElementById('statusActionBtn');
        if (!btn) return;
        const icon = btn.querySelector('i');
        const span = btn.querySelector('span');
        if (icon && iconClass) icon.className = iconClass;
        if (span && label) span.textContent = label;
    };

    // Utilidad para setear ícono/tooltip en botón mobile
    const setMobileButtonContent = (title, iconClass) => {
        const btn = document.getElementById('statusActionBtnMobile');
        if (!btn) return;
        const icon = btn.querySelector('i');
        if (icon && iconClass) icon.className = iconClass;
        if (title) btn.title = title;
    };

    // Mostrar/ocultar dropdowns y configurar acciones
    if (shouldBeDirectCloseButton) {
        dropdowns.forEach(dd => {
            dd.style.display = 'none';
        });

        const label = (directState === 'en-proceso') ? 'Reabrir ticket' : 'Cerrar ticket';
        const iconClass = (directState === 'en-proceso') ? 'bi bi-arrow-counterclockwise' : 'bi bi-x-circle-fill';

        setDesktopButtonContent(label, iconClass);
        setMobileButtonContent(label, iconClass);

        const desktopBtn = document.getElementById('statusActionBtn');
        const mobileBtn = document.getElementById('statusActionBtnMobile');

        if (desktopBtn) {
            desktopBtn.onclick = (event) => {
                if (event) event.stopPropagation();
                window.changeTicketStatus(directState);
            };
        }
        if (mobileBtn) {
            mobileBtn.onclick = (event) => {
                if (event) event.stopPropagation();
                window.changeTicketStatus(directState);
            };
        }
    } else {
        dropdowns.forEach(dd => {
            dd.style.display = '';
        });

        // Si el único estado permitido es "resuelto", el botón se entiende mejor como "Resolver"
        const onlyResuelto = allowedStates.length === 1 && allowedStates[0] === 'resuelto';
        if (onlyResuelto) {
            setDesktopButtonContent('Resolver', 'bi bi-check-circle-fill');
            setMobileButtonContent('Resolver ticket', 'bi bi-check-circle-fill');
        } else {
            setDesktopButtonContent('Estado', 'bi bi-arrow-repeat');
            setMobileButtonContent('Estado', 'bi bi-arrow-repeat');
        }

        const desktopBtn = document.getElementById('statusActionBtn');
        const mobileBtn = document.getElementById('statusActionBtnMobile');

        if (desktopBtn) {
            desktopBtn.onclick = (event) => toggleActionDropdown('statusDropdown', event);
        }
        if (mobileBtn) {
            mobileBtn.onclick = (event) => toggleActionDropdown('statusDropdownMobile', event);
        }
    }

    const hasAny = allowedStates.length > 0;
    btns.forEach(b => {
        b.disabled = !hasAny;
        if (!hasAny) {
            b.setAttribute('aria-disabled', 'true');
            b.title = 'No tienes permisos para cambiar el estado';
        } else {
            b.removeAttribute('aria-disabled');
        }
    });
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
