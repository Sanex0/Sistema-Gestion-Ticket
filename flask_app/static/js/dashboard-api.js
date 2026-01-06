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
    
    static async subirAdjunto(formData) {
        const token = AuthService.getToken();
        return await fetch(`${AUTH_CONFIG.API_BASE_URL}/adjuntos/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        }).then(res => res.json());
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
            
            // Calcular tickets abiertos (estados 1, 2, 3 = Nuevo, En Progreso, En Espera)
            const ticketsAbiertos = estadisticas.por_estado
                .filter(e => ['Nuevo', 'En Progreso', 'En Espera'].includes(e.estado))
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
                    total_tickets: 0
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
        const result = await DashboardAPI.getTickets({ ...filtros, limit: 10 });
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
            usuario_nombre: (t.usuario && (t.usuario.nombre || t.usuario.name)) || t.usuario_nombre || (t.usuario_nombre ? t.usuario_nombre : ''),
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
        }));

        renderTicketsRecientes(normalized);
    } catch (error) {
        console.error('Error al cargar tickets:', error);
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
        if (e === 'sin responder') return 'sin-respuesta';
        if (e === 'sin respuesta') return 'sin-respuesta';
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
        if (ticket.id_operador && ticket.operador_nombre) {
            const aceptado = ticket.operador_aceptado === true;
            if (aceptado) {
                operadorTexto = `<span class="text-primary"><i class="bi bi-person-check-fill"></i> ${ticket.operador_nombre}</span>`;
            } else {
                operadorTexto = `<span class="text-warning"><i class="bi bi-clock-history"></i> ${ticket.operador_nombre}</span>`;
            }
        }
        
        // Estilos para tickets sin asignar del emisor
        const rowStyle = sinAsignarMio ? 'opacity: 0.5; background-color: #f8f9fa; cursor: not-allowed;' : 'cursor: pointer;';
        const clickAction = sinAsignarMio ? '' : `onclick="verTicket(${ticket.id_ticket})"`;
        const statusMapped = mapearEstado(ticket.estado_desc);
        
        return `
        <tr style="${rowStyle}" ${clickAction}
            data-ticket-id="${ticket.id_ticket}"
            data-remitente-id="${ticket.id_operador_emisor || ''}"
            data-operador-id="${ticket.id_operador || ''}"
            data-depto-id="${ticket.id_depto || ''}"
            data-depto-owner-id="${ticket.id_depto_owner || ''}"
            data-prioridad="${ticket.id_prioridad || ''}"
            data-status="${statusMapped}">
            <td class="fw-semibold text-brand-blue">#${ticket.id_ticket}</td>
            <td>
                <div>${ticket.titulo || 'Sin título'}</div>
                ${sinAsignarMio ? '<span class="badge bg-warning text-dark mt-1"><i class="bi bi-hourglass-split"></i> Esperando atención</span>' : ''}
                <small class="text-muted d-md-none">${ticket.usuario_nombre || 'Sin usuario'}</small>
            </td>
            <td class="d-none d-md-table-cell">${ticket.usuario_nombre || 'Sin usuario'}</td>
            <td class="d-none d-md-table-cell"><small>${operadorTexto}</small></td>
            <td><span class="badge ${getPrioridadClass(ticket.id_prioridad)}">${ticket.prioridad_desc || 'Normal'}</span></td>
            <td>
                <span class="badge ${getEstadoBadgeClass(ticket.id_estado)}">${ticket.estado_desc || 'Nuevo'}</span>
                ${sinAsignar && !esMio ? '<span class="badge bg-info text-white ms-1"><i class="bi bi-hand-thumbs-up"></i> Disponible</span>' : ''}
            </td>
            <td class="d-none d-md-table-cell">
                ${sinAsignar && !esMio ? `
                    <button class="btn btn-sm btn-success me-1" onclick="event.stopPropagation(); mostrarModalTomarTicket(${ticket.id_ticket}, '${(ticket.titulo || '').replace(/'/g, "\\'")}')"
                        title="Tomar ticket">
                        <i class="bi bi-hand-thumbs-up"></i>
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation(); ${sinAsignarMio ? 'return false;' : `verTicket(${ticket.id_ticket})`}"
                    ${sinAsignarMio ? 'disabled' : ''}>
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
        1: 'prioridad-baja bg-success',
        2: 'prioridad-media bg-warning text-dark',
        3: 'prioridad-alta bg-danger',
        4: 'prioridad-urgente bg-danger'
    };
    return classes[idPrioridad] || 'bg-secondary';
}

function getEstadoBadgeClass(idEstado) {
    const classes = {
        1: 'bg-warning text-dark',  // Nuevo
        2: 'bg-info text-white',     // En proceso
        3: 'bg-success text-white',  // Cerrado
        4: 'bg-danger text-white'    // Rechazado
    };
    return classes[idEstado] || 'bg-secondary';
}

// Funciones auxiliares removidas - se usan tickets-reales.js para renderización
