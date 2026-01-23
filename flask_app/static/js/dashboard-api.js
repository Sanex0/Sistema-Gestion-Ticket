// ============================================
// API SERVICE PARA DASHBOARD - LIMPIO Y SIN ERRORES
// ============================================

class DashboardAPI {
    
    // ============================================
    // TICKETS
    // ============================================
    
    static async getTickets(filtros = {}) {
        const params = new URLSearchParams(filtros);
        return await apiRequest(`/tickets?${params.toString()}`);
    }

    static async getTicketById(id) {
        return await apiRequest(`/tickets/${id}`);
    }

    static async createTicket(ticketData) {
        return await apiRequest('/tickets', {
            method: 'POST',
            body: JSON.stringify(ticketData)
        });
    }

    static async updateTicket(id, ticketData) {
        return await apiRequest(`/tickets/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(ticketData)
        });
    }

    static async deleteTicket(id) {
        return await apiRequest(`/tickets/${id}`, {
            method: 'DELETE'
        });
    }

    static async cambiarEstadoTicket(id, nuevoEstado) {
        return await apiRequest(`/tickets/${id}/estado`, {
            method: 'PATCH',
            body: JSON.stringify({ id_estado: nuevoEstado })
        });
    }

    static async cambiarPrioridadTicket(id, nuevaPrioridad) {
        return await apiRequest(`/tickets/${id}/prioridad`, {
            method: 'PATCH',
            body: JSON.stringify({ id_prioridad: nuevaPrioridad })
        });
    }

    static async asignarOperador(idTicket, idOperador) {
        return await apiRequest(`/tickets/${idTicket}/asignar`, {
            method: 'POST',
            body: JSON.stringify({ id_operador: idOperador })
        });
    }

    // ============================================
    // MENSAJES
    // ============================================
    
    static async getMensajesPorTicket(idTicket) {
        return await apiRequest(`/tickets/${idTicket}/mensajes`);
    }

    static async enviarMensaje(mensajeData) {
        return await apiRequest('/mensajes', {
            method: 'POST',
            body: JSON.stringify(mensajeData)
        });
    }

    // ============================================
    // CATÁLOGOS
    // ============================================
    
    static async getEstados() {
        return await apiRequest('/catalogos/estados');
    }

    static async getPrioridades() {
        return await apiRequest('/catalogos/prioridades');
    }

    static async getClubes() {
        return await apiRequest('/catalogos/clubes');
    }

    static async getSLAs() {
        return await apiRequest('/catalogos/slas');
    }

    static async getCanales() {
        return await apiRequest('/catalogos/canales');
    }

    static async getRoles() {
        return await apiRequest('/catalogos/roles');
    }

    // ============================================
    // OPERADORES
    // ============================================
    
    static async getOperadores() {
        return await apiRequest('/operadores');
    }

    static async getOperadorById(id) {
        return await apiRequest(`/operadores/${id}`);
    }

    static async getRolesOperadores() {
        return await apiRequest('/operadores/roles');
    }

    // ============================================
    // DEPARTAMENTOS
    // ============================================
    
    static async getDepartamentos() {
        return await apiRequest('/departamentos');
    }

    static async getDepartamentoById(id) {
        return await apiRequest(`/departamentos/${id}`);
    }

    static async crearDepartamento(data) {
        return await apiRequest('/departamentos', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async getMiembrosDepartamento(idDepto) {
        return await apiRequest(`/departamentos/${idDepto}/miembros`);
    }

    static async agregarMiembroDepartamento(idDepto, data) {
        return await apiRequest(`/departamentos/${idDepto}/miembros`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // ============================================
    // ETIQUETAS
    // ============================================
    
    static async getEtiquetas() {
        return await apiRequest('/etiquetas');
    }

    static async crearEtiqueta(data) {
        return await apiRequest('/etiquetas', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async asignarEtiqueta(idTicket, idEtiqueta) {
        return await apiRequest(`/etiquetas/${idEtiqueta}/asignar`, {
            method: 'POST',
            body: JSON.stringify({ id_ticket: idTicket })
        });
    }

    static async getEtiquetasTicket(idTicket) {
        return await apiRequest(`/etiquetas/ticket/${idTicket}`);
    }

    // ============================================
    // ADJUNTOS
    // ============================================

    static async subirAdjuntoMensaje(mensajeId, file) {
        const token = AuthService.getToken();
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${AUTH_CONFIG.API_BASE_URL}/mensajes/${mensajeId}/adjuntos`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        let data = null;
        try {
            data = await res.json();
        } catch (e) {
            data = null;
        }

        if (!res.ok) {
            return data || { success: false, error: `Error HTTP ${res.status}` };
        }

        return data || { success: false, error: 'Respuesta inválida del servidor' };
    }

    // Compatibilidad: algunos módulos usaban /adjuntos/upload
    static async subirAdjuntoLegacy(mensajeId, file) {
        const token = AuthService.getToken();
        const formData = new FormData();
        formData.append('mensaje_id', String(mensajeId));
        formData.append('file', file);
        const res = await fetch(`${AUTH_CONFIG.API_BASE_URL}/adjuntos/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        let data = null;
        try {
            data = await res.json();
        } catch (e) {
            data = null;
        }

        if (!res.ok) {
            return data || { success: false, error: `Error HTTP ${res.status}` };
        }

        return data || { success: false, error: 'Respuesta inválida del servidor' };
    }

    // ============================================
    // ESTADÍSTICAS Y KPIs
    // ============================================
    
    static async getEstadisticas() {
        return await apiRequest('/tickets/estadisticas');
    }

    static async buscarTicketsAvanzado(filtros) {
        return await apiRequest('/tickets/search', {
            method: 'POST',
            body: JSON.stringify(filtros)
        });
    }

    static async getHistorialTicket(idTicket) {
        return await apiRequest(`/tickets/${idTicket}/historial`);
    }
    
    static async getKPIs() {
        try {
            // Obtener estadísticas del backend
            const stats = await this.getEstadisticas();
            
            if (!stats.success) {
                throw new Error('Error al obtener estadísticas');
            }

            const { estadisticas } = stats;

            // Preferir KPIs calculados por el backend (evita inconsistencias por nombres de estados)
            if (estadisticas?.kpis) {
                return {
                    success: true,
                    kpis: {
                        tickets_abiertos: estadisticas.kpis.tickets_abiertos ?? 0,
                        nuevos_hoy: estadisticas.kpis.nuevos_hoy ?? 0,
                        mis_tickets: estadisticas.kpis.mis_tickets ?? 0,
                        total_tickets: estadisticas.kpis.total_tickets ?? estadisticas.total_tickets ?? 0,
                        resueltos_hoy: estadisticas.kpis.resueltos_hoy ?? 0,
                        satisfaccion_pct: (typeof estadisticas.kpis.satisfaccion_pct === 'number') ? estadisticas.kpis.satisfaccion_pct : null,
                        por_estado: estadisticas.por_estado,
                        por_prioridad: estadisticas.por_prioridad,
                        tiempo_resolucion: estadisticas.tiempo_resolucion
                    }
                };
            }
            
            // Calcular tickets abiertos (estados 1, 2, 3 = Nuevo, En Progreso, En Espera)
            const ticketsAbiertos = estadisticas.por_estado
                .filter(e => ['Nuevo', 'En Progreso', 'En Proceso', 'En Espera', 'Pendiente'].includes(e.estado))
                .reduce((sum, e) => sum + (e.total || 0), 0);
            
            // Tickets nuevos hoy
            const nuevosHoy = estadisticas.por_periodo?.hoy || 0;
            
            // Obtener mis tickets (tickets asignados al usuario actual)
            const userInfo = AuthService.getUserInfo();
            const misTicketsResponse = await this.getTickets({ 
                operador_id: userInfo?.id,
                limit: 1000 
            });
            const misTickets = misTicketsResponse.total || 0;

            return {
                success: true,
                kpis: {
                    tickets_abiertos: ticketsAbiertos,
                    nuevos_hoy: nuevosHoy,
                    mis_tickets: misTickets,
                    resueltos_hoy: 0,
                    satisfaccion_pct: null,
                    por_estado: estadisticas.por_estado,
                    por_prioridad: estadisticas.por_prioridad,
                    tiempo_resolucion: estadisticas.tiempo_resolucion
                }
            };
        } catch (error) {
            console.error('Error al obtener KPIs:', error);
            return {
                success: false,
                kpis: {
                    tickets_abiertos: 0,
                    nuevos_hoy: 0,
                    mis_tickets: 0,
                    total_tickets: 0,
                    resueltos_hoy: 0,
                    satisfaccion_pct: null
                }
            };
        }
    }
}

// ============================================
// INICIALIZACIÓN AL CARGAR DASHBOARD
// ============================================

document.addEventListener('DOMContentLoaded', async function() {
    try {
        if (!AuthService.isAuthenticated()) {
            window.location.href = '/';
            return;
        }

        const user = AuthService.getCurrentUser();
        if (user) {
            const userNameEl = document.getElementById('userName');
            const userEmailEl = document.getElementById('userEmail');
            const userRoleEl = document.getElementById('userRole');
            
            if (userNameEl) userNameEl.textContent = user.nombre;
            if (userEmailEl) userEmailEl.textContent = user.email;
            if (userRoleEl) userRoleEl.textContent = user.rol_nombre || user.rol;
        }

        // Cargar datos reales del dashboard
        // - KPIs vienen de /api/tickets/estadisticas
        // - Tickets recientes, catálogos
        try {
            await cargarKPIs();
            await cargarCatalogos();
            await cargarTickets();
        } catch (e) {
            console.warn('⚠️ No se pudo cargar datos iniciales del dashboard:', e);
        }

        console.log('✅ Dashboard inicializado correctamente');
    } catch (error) {
        console.error('❌ Error al inicializar dashboard:', error);
    }
});

// ============================================
// FUNCIONES DE CARGA DE DATOS
// ============================================

async function cargarKPIs() {
    try {
        const result = await DashboardAPI.getKPIs();
        
        if (result.success) {
            const kpis = result.kpis;
            
            // Actualizar valores en el DOM
            const ticketsAbiertosEl = document.getElementById('kpi-tickets-abiertos');
            const nuevosHoyEl = document.getElementById('kpi-nuevos-hoy');
            const misTicketsEl = document.getElementById('kpi-mis-tickets');
            
            if (ticketsAbiertosEl) ticketsAbiertosEl.textContent = kpis.tickets_abiertos;
            if (nuevosHoyEl) nuevosHoyEl.textContent = kpis.nuevos_hoy;
            if (misTicketsEl) misTicketsEl.textContent = kpis.mis_tickets;

            // Métricas detalladas (Home)
            const resueltosHoyEl = document.getElementById('kpiResueltosHoy');
            if (resueltosHoyEl) resueltosHoyEl.textContent = String(kpis.resueltos_hoy ?? 0);

            const pendientesEl = document.getElementById('kpiPendientes');
            if (pendientesEl) pendientesEl.textContent = String(kpis.tickets_abiertos ?? 0);

            const pendientesBadgesEl = document.getElementById('kpiPendientesBadges');
            if (pendientesBadgesEl) {
                const porEstado = Array.isArray(kpis.por_estado) ? kpis.por_estado : [];
                const abiertos = porEstado
                    .filter(e => String(e.estado || '').toLowerCase() !== 'cerrado')
                    .filter(e => (e.total || 0) > 0);

                if (abiertos.length === 0) {
                    pendientesBadgesEl.innerHTML = '<span class="text-muted small">Sin datos</span>';
                } else {
                    // Top 3 estados abiertos
                    const top = abiertos.slice(0, 3);
                    pendientesBadgesEl.innerHTML = top.map(e => {
                        const idEstado = e.id_estado ?? e.idEstado;
                        const label = e.estado || 'Pendiente';
                        const total = e.total || 0;
                        return `<span class="badge ${getEstadoBadgeClass(idEstado)} me-1">${label}: ${total}</span>`;
                    }).join('');
                }
            }

            // Satisfacción: solo si hay fuente real
            const satisfaccionEl = document.getElementById('kpiSatisfaccion');
            const satisfaccionBarEl = document.getElementById('kpiSatisfaccionBar');
            if (satisfaccionEl) {
                if (typeof kpis.satisfaccion_pct === 'number') {
                    const pct = Math.max(0, Math.min(100, Math.round(kpis.satisfaccion_pct)));
                    satisfaccionEl.textContent = `${pct}%`;
                    if (satisfaccionBarEl) satisfaccionBarEl.style.width = `${pct}%`;
                } else {
                    satisfaccionEl.textContent = 'N/D';
                    satisfaccionEl.title = 'Satisfacción aún no implementada en backend';
                    if (satisfaccionBarEl) satisfaccionBarEl.style.width = '0%';
                }
            }

            // Si hay datos de estadísticas detalladas, renderizar gráficos
            if (kpis.por_estado) {
                renderGraficoEstados(kpis.por_estado);
            }
            if (kpis.por_prioridad) {
                renderGraficoPrioridades(kpis.por_prioridad);
            }
        }
    } catch (error) {
        console.error('Error al cargar KPIs:', error);
    }
}

function renderGraficoEstados(porEstado) {
    // TODO: Implementar con Chart.js cuando esté disponible
    console.log('Datos de estados:', porEstado);
}

function renderGraficoPrioridades(porPrioridad) {
    // TODO: Implementar con Chart.js cuando esté disponible
    console.log('Datos de prioridades:', porPrioridad);
}

async function cargarTickets(filtros = {}) {
    try {
        // Para "Tickets Recientes" necesitamos filtrar por rol en el frontend.
        // Pedimos un lote mayor para poder quedarnos con los 5 más recientes del scope.
        const requested = Number(filtros.limit) || 0;
        const fetchLimit = Math.max(50, requested, 5);
        const result = await DashboardAPI.getTickets({ ...filtros, limit: fetchLimit, offset: 0 });
        let ticketsList = [];

        if (!result) return;

        if (result.success) {
            // soportar distintas formas de respuesta: { success, tickets, total } o { success, data }
            ticketsList = result.tickets || result.data || [];
        } else {
            // en algunos endpoints la respuesta puede venir sin success
            ticketsList = result.data || result.tickets || [];
        }

        // Normalizar estructura para el renderer antiguo
        const normalized = ticketsList.map(t => ({
            id_ticket: t.id_ticket || t.id || t.idTicket,
            titulo: t.titulo || t.title,
            usuario_nombre: t.emisor_nombre || t.operador_emisor_nombre || (t.usuario && (t.usuario.nombre || t.usuario.name)) || t.usuario_nombre || '',
            emisor_nombre: t.emisor_nombre || t.operador_emisor_nombre || (t.usuario && (t.usuario.nombre || t.usuario.name)) || t.usuario_nombre || '',
            prioridad_desc: t.prioridad || t.prioridad_desc || t.prioridadDescripcion || '',
            estado_desc: t.estado || t.estado_desc || t.estadoDescripcion || '',
            id_prioridad: t.id_prioridad || t.idPrioridad || null,
            id_estado: t.id_estado || t.idEstado || null,
            id_operador: t.id_operador,
            id_operador_emisor: t.id_operador_emisor,
            id_depto: t.id_depto,
            id_depto_owner: t.id_depto_owner,
            operador_nombre: t.operador_nombre,
            operador_aceptado: t.operador_aceptado
            ,
            // Intentar preservar alguna fecha de última actividad si viene del backend
            ultima_actividad: t.ultima_actividad || t.fecha_ultima_actividad || t.fecha_ultimo_movimiento || t.updated_at || t.updatedAt || t.fecha_modificacion || t.ultima_modificacion || t.fecha_actualizacion || null
        }));

        // Aplicar scope según rol:
        // - Admin: ve todo el sistema
        // - Supervisor: ve solo los tickets de su(s) departamento(s)
        // - Agente: ve solo los tickets creados por él
        let perfil = window.perfilUsuario;
        if (!perfil) {
            try {
                const me = await apiRequest('/operadores/me');
                if (me && me.success && me.operador) {
                    perfil = me.operador;
                    window.perfilUsuario = me.operador;
                }
            } catch (e) {
                // Si falla, seguimos sin perfil (fallback: no filtramos extra)
                console.warn('No se pudo obtener perfil para filtrar tickets recientes:', e);
            }
        }

        const idUsuarioActual = perfil?.id_operador ?? perfil?.operador_id ?? perfil?.id;
        const esAdmin = !!perfil?.es_admin;
        const esSupervisor = !!perfil?.es_supervisor;
        const deptos = Array.isArray(perfil?.departamentos) ? perfil.departamentos : [];

        const perteneceAMisDeptos = (ticket) => {
            if (!deptos || deptos.length === 0) return false;
            const deptoTicket = ticket.id_depto || ticket.id_depto_owner;
            if (!deptoTicket) return false;
            return deptos.some(d => String(d.id_depto || d.id_departamento) === String(deptoTicket));
        };

        let scoped = normalized;
        if (perfil) {
            if (esAdmin) {
                scoped = normalized;
            } else if (esSupervisor) {
                scoped = normalized.filter(perteneceAMisDeptos);
            } else {
                // Para agentes: mostrar tickets que creó o que están asignados a él
                scoped = normalized.filter(t => String(t.id_operador_emisor || '') === String(idUsuarioActual || '') || String(t.id_operador || '') === String(idUsuarioActual || ''));
            }
        }

        // Si faltan fechas de última actividad, intentar obtenerlas desde el historial del ticket
        async function obtenerUltimaFechaHistorial(idTicket) {
            try {
                const res = await DashboardAPI.getHistorialTicket(idTicket);
                const items = res?.data || res?.historial || res || [];
                if (!Array.isArray(items) || items.length === 0) return null;
                // Buscar la fecha máxima en la propiedad 'fecha' (fallbacks comunes)
                let maxTs = 0;
                items.forEach(it => {
                    const f = it.fecha || it.created_at || it.createdAt || it.fecha_creacion || it.timestamp || it.date;
                    if (!f) return;
                    const t = Date.parse(f);
                    if (!isNaN(t) && t > maxTs) maxTs = t;
                });
                return maxTs ? new Date(maxTs).toISOString() : null;
            } catch (e) {
                return null;
            }
        }

        const faltantes = scoped.filter(t => !t.ultima_actividad);
        if (faltantes.length > 0) {
            // Limitar concurrencia para no golpear el API
            const concurrency = 6;
            for (let i = 0; i < faltantes.length; i += concurrency) {
                const batch = faltantes.slice(i, i + concurrency);
                await Promise.all(batch.map(async ticket => {
                    try {
                        const f = await obtenerUltimaFechaHistorial(ticket.id_ticket);
                        if (f) ticket.ultima_actividad = f;
                    } catch (e) {
                        // ignore
                    }
                }));
            }
        }

        // Ordenar por última actividad (si existe) descendente. Si no hay fecha, usar id desc.
        scoped.sort((a, b) => {
            const da = a.ultima_actividad ? Date.parse(a.ultima_actividad) : 0;
            const db = b.ultima_actividad ? Date.parse(b.ultima_actividad) : 0;
            if (da || db) return db - da;
            return (b.id_ticket || 0) - (a.id_ticket || 0);
        });

        renderTicketsRecientes(scoped.slice(0, 5));
    } catch (error) {
        console.error('Error al cargar tickets:', error);
    }
}

// Función pública para recargar solo los últimos tickets desde la UI
async function refreshRecentTickets() {
    const btn = document.getElementById('refreshRecentTicketsBtn');
    if (btn) {
        btn.disabled = true;
    }
    let origHtml = null;
    if (btn) {
        origHtml = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        btn.classList.add('rotating');
    }

    try {
        await cargarTickets();
    } catch (e) {
        console.error('Error al refrescar últimos tickets:', e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml || '<i class="bi bi-arrow-clockwise"></i>';
            btn.classList.remove('rotating');
        }
    }
}

function renderTicketsRecientes(tickets) {
    const tbody = document.getElementById('recent-tickets-tbody');
    if (!tbody) return;

    if (!tickets || tickets.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted py-4">
                    <i class="bi bi-inbox fs-3 d-block mb-2"></i>
                    No hay tickets recientes
                </td>
            </tr>
        `;
        return;
    }

    // Obtener ID del usuario actual desde el perfil
    const idUsuarioActual = window.perfilUsuario?.id_operador ?? window.perfilUsuario?.operador_id ?? window.perfilUsuario?.id;

    // Helpers: escape, snippet y timeAgo
    function escapeHtml(unsafe) {
        if (!unsafe && unsafe !== 0) return '';
        return String(unsafe)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function snippet(text, maxLen) {
        if (!text) return '';
        const s = String(text).trim();
        if (s.length <= maxLen) return s;
        return s.slice(0, maxLen - 1).trim() + '…';
    }

    function timeAgo(dateStr) {
        if (!dateStr) return '';
        const d = Date.parse(dateStr);
        if (isNaN(d)) return '';
        const diff = Math.floor((Date.now() - d) / 1000);
        if (diff < 60) return `${diff}s`;
        if (diff < 3600) return `${Math.floor(diff/60)}m`;
        if (diff < 86400) return `${Math.floor(diff/3600)}h`;
        const days = Math.floor(diff/86400);
        return `${days}d`;
    }
    
    // Función auxiliar para mapear estado (duplicada de tickets-reales.js para consistencia)
    const mapearEstado = (estado) => {
        if (!estado) return 'pendiente';
        const e = String(estado).toLowerCase().replace(/\s+/g, ' ').trim();
        if (e === 'nuevo') return 'pendiente';
        if (e === 'pendiente') return 'pendiente';
        if (e === 'en proceso') return 'en-proceso';
        if (e === 'en progreso') return 'en-proceso';
        if (e === 'resuelto') return 'resuelto';
        if (e === 'cerrado') return 'cerrado';
        if (e === 'sin responder') return 'por-tomar';
        if (e === 'sin respuesta') return 'por-tomar';
        if (e === 'rechazado') return 'rechazado';
        return 'pendiente';
    };
    
    tbody.innerHTML = tickets.map(ticket => {
        // Verificar si el ticket está sin asignar
        const sinAsignar = !ticket.id_operador;
        const esMio = !!idUsuarioActual && String(ticket.id_operador_emisor) === String(idUsuarioActual);
        const sinAsignarMio = sinAsignar && esMio;
        
        // Determinar texto del operador asignado
        let operadorTexto = '<span class="text-warning"><i class="bi bi-hourglass-split"></i> Sin asignar</span>';
        let operadorPlain = 'Sin asignar';
        if (ticket.id_operador && ticket.operador_nombre) {
            operadorPlain = ticket.operador_nombre;
            const aceptado = ticket.operador_aceptado === true;
            if (aceptado) {
                operadorTexto = `<span class="text-primary"><i class="bi bi-person-check-fill"></i> ${ticket.operador_nombre}</span>`;
            } else {
                operadorTexto = `<span class="text-warning"><i class="bi bi-clock-history"></i> ${ticket.operador_nombre}</span>`;
            }
        }
        
        // Interacción de fila
        const rowClass = sinAsignarMio ? 'is-disabled' : 'is-clickable';
        const clickAction = sinAsignarMio ? '' : `onclick="verTicket(${ticket.id_ticket})"`;
        const statusMapped = mapearEstado(ticket.estado_desc);
        
        return `
        <tr class="${rowClass}" ${clickAction}
            data-ticket-id="${ticket.id_ticket}"
            data-remitente-id="${ticket.id_operador_emisor || ''}"
            data-operador-id="${ticket.id_operador || ''}"
            data-depto-id="${ticket.id_depto || ''}"
            data-depto-owner-id="${ticket.id_depto_owner || ''}"
            data-prioridad="${ticket.id_prioridad || ''}"
            data-status="${statusMapped}">
            <td class="fw-semibold text-brand-blue col-id">#${ticket.id_ticket}</td>
            <td class="col-asunto">
                <div class="ticket-subject">${escapeHtml(ticket.titulo || 'Sin título')}</div>
                ${sinAsignarMio ? '<small class="ticket-substatus d-block mt-1"><span class="badge status-nuevo text-white"><i class="bi bi-hourglass-split me-1"></i>Esperando atención</span></small>' : ''}
                <small class="text-muted ticket-meta d-block d-md-none">${escapeHtml(ticket.emisor_nombre || ticket.usuario_nombre || 'Sin emisor')} · ${escapeHtml(operadorPlain)}</small>
                <small class="text-muted d-none d-md-block ticket-meta">${escapeHtml(ticket.emisor_nombre || ticket.usuario_nombre || 'Sin emisor')} · ${escapeHtml(operadorPlain)} · ${escapeHtml(timeAgo(ticket.ultima_actividad || ticket.fecha_creacion || ''))}</small>
                ${(ticket.ultimo_mensaje || ticket.descripcion) ? `<small class="text-muted ticket-snippet d-block mt-1" title="${escapeHtml(ticket.ultimo_mensaje || ticket.descripcion || '')}">${escapeHtml(snippet(ticket.ultimo_mensaje || ticket.descripcion || '', 75))}</small>` : ''}
            </td>
            <td class="d-none d-md-table-cell col-emisor"><span class="cell-ellipsis">${ticket.emisor_nombre || ticket.usuario_nombre || 'Sin emisor'}</span></td>
            <td class="d-none d-md-table-cell col-receptor"><span class="cell-ellipsis">${operadorTexto}</span></td>
            <td class="col-prioridad"><span class="badge ${getPrioridadClass(ticket.id_prioridad)}">${ticket.prioridad_desc || 'Normal'}</span></td>
            <td class="col-estado">
                <span class="badge ${getEstadoBadgeClass(ticket.id_estado)}">${ticket.estado_desc || 'Nuevo'}</span>
                ${sinAsignar && !esMio ? '<span class="badge bg-info text-white ms-1 d-inline-block d-md-none"><i class="bi bi-hand-thumbs-up"></i> Disponible</span>' : ''}
            </td>
            <td class="d-none d-md-table-cell col-acciones action-cell">
                ${sinAsignar && !esMio ? `
                    <button class="btn btn-sm btn-success me-1" onclick="event.stopPropagation(); mostrarModalTomarTicket(${ticket.id_ticket}, '${(ticket.titulo || '').replace(/'/g, "\\'")}')"
                        title="Tomar ticket">
                        <i class="bi bi-hand-thumbs-up"></i>
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation(); ${sinAsignarMio ? 'return false;' : `abrirDetalleTicket(${ticket.id_ticket})`}"
                    ${sinAsignarMio ? 'disabled' : ''}
                    title="Ver detalle del ticket">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        </tr>
        `;
    }).join('');
}

async function cargarCatalogos() {
    try {
        const [estados, prioridades, clubes, slas] = await Promise.all([
            DashboardAPI.getEstados(),
            DashboardAPI.getPrioridades(),
            DashboardAPI.getClubes(),
            DashboardAPI.getSLAs()
        ]);

        // Guardar en variable global para uso en formularios
        window.catalogos = {
            estados: estados.data || [],
            prioridades: prioridades.data || [],
            clubes: clubes.data || [],
            slas: slas.data || []
        };

        // Llenar selectores
        llenarSelector('ticketEstado', estados.data, 'id_estado', 'descripcion');
        llenarSelector('ticketPrioridad', prioridades.data, 'id_prioridad', 'descripcion');
        llenarSelector('ticketClub', clubes.data, 'id_club', 'nombre');
        llenarSelector('ticketSLA', slas.data, 'id_sla', 'nombre');
        
    } catch (error) {
        console.error('Error al cargar catálogos:', error);
    }
}

function llenarSelector(elementId, items, valueKey, textKey) {
    const select = document.getElementById(elementId);
    if (!select) return;

    select.innerHTML = '<option value="">Seleccionar...</option>';
    
    items?.forEach(item => {
        const option = document.createElement('option');
        option.value = item[valueKey];
        option.textContent = item[textKey];
        select.appendChild(option);
    });
}

function getPrioridadClass(idPrioridad) {
    const classes = {
        1: 'prioridad-critica',   // Urgente - Rojo
        2: 'prioridad-alta',      // Alta - Naranja
        3: 'prioridad-media',     // Media - Azul 
        4: 'prioridad-baja'       // Baja - Verde
    };
    return classes[idPrioridad] || 'bg-secondary';
}

function getEstadoBadgeClass(idEstado) {
    const classes = {
        1: 'status-nuevo text-dark',        // Nuevo/Pendiente (amarillo)
        2: 'status-en-proceso text-white',  // En Proceso (cyan)
        3: 'status-resuelto text-white',    // Resuelto (verde)
        4: 'status-closed text-white',      // Cerrado (gris)
        5: 'status-pendiente text-dark'     // Sin responder / Pendiente (rojo/yellow)
    };
    return classes[idEstado] || 'status-closed';
}

// Funciones auxiliares removidas - se usan tickets-reales.js para renderización
