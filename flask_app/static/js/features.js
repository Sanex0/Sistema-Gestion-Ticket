// ============================================
// SISTEMA DE ARCHIVOS ADJUNTOS
// ============================================

let attachedFiles = [];

function initializeFileUpload(ticketId) {
    attachedFiles = [];
    updateAttachmentList();
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    
    files.forEach(file => {
        // Validar tamaño (máximo 10MB)
        if (file.size > 10 * 1024 * 1024) {
            showToast('Error', `El archivo ${file.name} excede el tamaño máximo de 10MB`, 'danger');
            return;
        }
        
        // Validar tipo de archivo
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 
                             'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                             'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             'text/plain', 'application/zip'];
        
        if (!allowedTypes.includes(file.type)) {
            showToast('Error', `Tipo de archivo no permitido: ${file.name}`, 'danger');
            return;
        }
        
        const fileObj = {
            id: Date.now() + Math.random(),
            file: file,
            name: file.name,
            size: formatFileSize(file.size),
            type: file.type,
            icon: getFileIcon(file.type)
        };
        
        attachedFiles.push(fileObj);
    });
    
    updateAttachmentList();
    event.target.value = ''; // Reset input
}

function removeAttachment(fileId) {
    attachedFiles = attachedFiles.filter(f => f.id !== fileId);
    updateAttachmentList();
}

function updateAttachmentList() {
    const container = document.getElementById('attachmentList');
    const countBadge = document.getElementById('attachmentCount');
    
    if (!container) return;
    
    if (attachedFiles.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-3"><i class="bi bi-paperclip"></i> No hay archivos adjuntos</p>';
        if (countBadge) countBadge.textContent = '0';
        return;
    }
    
    if (countBadge) countBadge.textContent = attachedFiles.length;
    
    container.innerHTML = attachedFiles.map(file => `
        <div class="attachment-item" data-file-id="${file.id}">
            <div class="attachment-icon">
                <i class="bi bi-${file.icon}"></i>
            </div>
            <div class="attachment-info">
                <div class="attachment-name">${file.name}</div>
                <div class="attachment-size">${file.size}</div>
            </div>
            <button class="btn-remove-attachment" onclick="removeAttachment(${file.id})" title="Eliminar">
                <i class="bi bi-x-lg"></i>
            </button>
        </div>
    `).join('');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function getFileIcon(type) {
    if (type.startsWith('image/')) return 'file-image';
    if (type === 'application/pdf') return 'file-pdf';
    if (type.includes('word')) return 'file-word';
    if (type.includes('excel') || type.includes('spreadsheet')) return 'file-excel';
    if (type.includes('zip')) return 'file-zip';
    return 'file-earmark';
}

// ============================================
// SISTEMA DE ETIQUETAS/TAGS
// ============================================

const availableTags = [
    { id: 1, name: 'Urgente', color: '#dc3545' },
    { id: 2, name: 'Bug', color: '#fd7e14' },
    { id: 3, name: 'Feature', color: '#0dcaf0' },
    { id: 4, name: 'Soporte', color: '#198754' },
    { id: 5, name: 'Consulta', color: '#6f42c1' },
    { id: 6, name: 'Pago', color: '#ffc107' },
    { id: 7, name: 'Técnico', color: '#0d6efd' },
    { id: 8, name: 'Comercial', color: '#20c997' }
];

let selectedTags = [];

function initializeTags() {
    renderTagSelector();
    updateSelectedTags();
}

function renderTagSelector() {
    const container = document.getElementById('tagSelector');
    if (!container) return;
    
    container.innerHTML = availableTags.map(tag => `
        <button class="tag-option ${selectedTags.includes(tag.id) ? 'active' : ''}" 
                onclick="toggleTag(${tag.id})"
                style="--tag-color: ${tag.color}">
            <i class="bi bi-tag-fill"></i> ${tag.name}
        </button>
    `).join('');
}

function toggleTag(tagId) {
    if (selectedTags.includes(tagId)) {
        selectedTags = selectedTags.filter(id => id !== tagId);
    } else {
        selectedTags.push(tagId);
    }
    renderTagSelector();
    updateSelectedTags();
}

function updateSelectedTags() {
    const container = document.getElementById('selectedTagsDisplay');
    if (!container) return;
    
    if (selectedTags.length === 0) {
        container.innerHTML = '<span class="text-muted">Sin etiquetas</span>';
        return;
    }
    
    const tags = selectedTags.map(id => availableTags.find(t => t.id === id));
    container.innerHTML = tags.map(tag => `
        <span class="ticket-tag" style="background-color: ${tag.color}20; color: ${tag.color}; border-color: ${tag.color};">
            <i class="bi bi-tag-fill"></i> ${tag.name}
            <button class="tag-remove" onclick="toggleTag(${tag.id})">
                <i class="bi bi-x"></i>
            </button>
        </span>
    `).join('');
}

// ============================================
// SISTEMA DE CALIFICACIÓN/FEEDBACK
// ============================================

let currentRating = 0;

function openRatingModal(ticketId) {
    currentRating = 0;
    updateRatingStars();
    document.getElementById('feedbackText').value = '';
    const modal = new bootstrap.Modal(document.getElementById('ratingModal'));
    modal.show();
}

function setRating(stars) {
    currentRating = stars;
    updateRatingStars();
}

function updateRatingStars() {
    for (let i = 1; i <= 5; i++) {
        const star = document.getElementById(`star${i}`);
        if (star) {
            if (i <= currentRating) {
                star.classList.add('active');
            } else {
                star.classList.remove('active');
            }
        }
    }
}

function submitRating() {
    if (currentRating === 0) {
        showToast('Error', 'Por favor selecciona una calificación', 'warning');
        return;
    }
    
    const feedback = document.getElementById('feedbackText').value;
    
    // Aquí irá la llamada al backend
    console.log('Rating:', currentRating, 'Feedback:', feedback);
    
    showToast('¡Gracias!', 'Tu calificación ha sido enviada', 'success');
    bootstrap.Modal.getInstance(document.getElementById('ratingModal')).hide();
}

// ============================================
// NOTIFICACIONES EN TIEMPO REAL (Mejoradas)
// ============================================

let notificationsList = [
    {
        id: 1,
        type: 'ticket',
        title: 'Nuevo ticket asignado',
        message: 'Se te ha asignado el ticket #1005',
        time: 'Hace 2 minutos',
        read: false,
        icon: 'bi-ticket-perforated',
        color: '#0dcaf0'
    },
    {
        id: 2,
        type: 'response',
        title: 'Nueva respuesta',
        message: 'Juan Pérez respondió al ticket #1001',
        time: 'Hace 15 minutos',
        read: false,
        icon: 'bi-reply-fill',
        color: '#198754'
    },
    {
        id: 3,
        type: 'alert',
        title: 'Ticket urgente',
        message: 'El ticket #1003 requiere atención inmediata',
        time: 'Hace 1 hora',
        read: false,
        icon: 'bi-exclamation-triangle-fill',
        color: '#dc3545'
    },
    {
        id: 4,
        type: 'system',
        title: 'Actualización del sistema',
        message: 'Nueva versión disponible',
        time: 'Hace 3 horas',
        read: true,
        icon: 'bi-info-circle-fill',
        color: '#6f42c1'
    }
];

function loadNotifications() {
    const container = document.getElementById('notificationsList');
    if (!container) return;
    
    const unreadCount = notificationsList.filter(n => !n.read).length;
    document.getElementById('unreadCount').textContent = unreadCount;
    document.getElementById('notifBadgeMobile').textContent = unreadCount;
    
    if (notificationsList.length === 0) {
        container.innerHTML = '<div class="text-center py-4 text-muted">No hay notificaciones</div>';
        return;
    }
    
    container.innerHTML = notificationsList.map(notif => `
        <div class="notification-item ${notif.read ? 'read' : ''}" onclick="markAsRead(${notif.id})">
            <div class="notification-icon" style="background-color: ${notif.color}20; color: ${notif.color};">
                <i class="bi ${notif.icon}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-title">${notif.title}</div>
                <div class="notification-message">${notif.message}</div>
                <div class="notification-time">${notif.time}</div>
            </div>
            ${!notif.read ? '<span class="notification-unread-dot"></span>' : ''}
        </div>
    `).join('');
}

function markAsRead(notifId) {
    const notif = notificationsList.find(n => n.id === notifId);
    if (notif) {
        notif.read = true;
        loadNotifications();
    }
}

function markAllAsRead() {
    notificationsList.forEach(n => n.read = true);
    loadNotifications();
}

// Simular notificaciones en tiempo real
function simulateRealTimeNotifications() {
    setInterval(() => {
        const types = ['ticket', 'response', 'alert', 'system'];
        const type = types[Math.floor(Math.random() * types.length)];
        
        const newNotif = {
            id: Date.now(),
            type: type,
            title: 'Nueva notificación',
            message: 'Este es un mensaje de prueba',
            time: 'Justo ahora',
            read: false,
            icon: type === 'ticket' ? 'bi-ticket-perforated' : 
                  type === 'response' ? 'bi-reply-fill' :
                  type === 'alert' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill',
            color: type === 'ticket' ? '#0dcaf0' :
                   type === 'response' ? '#198754' :
                   type === 'alert' ? '#dc3545' : '#6f42c1'
        };
        
        notificationsList.unshift(newNotif);
        if (notificationsList.length > 20) notificationsList.pop();
        
        loadNotifications();
        showNotificationToast(newNotif);
    }, 30000); // Cada 30 segundos
}

function showNotificationToast(notif) {
    showToast(notif.title, notif.message, 'info');
}

// ============================================
// REGISTRO DE AUDITORÍA
// ============================================

const auditLogs = [
    {
        id: 1,
        timestamp: '2025-12-17 10:30:25',
        user: 'Admin',
        action: 'Ticket creado',
        details: 'Ticket #1001 creado por Juan Pérez',
        type: 'create',
        icon: 'bi-plus-circle',
        color: '#198754'
    },
    {
        id: 2,
        timestamp: '2025-12-17 10:32:15',
        user: 'Agente1',
        action: 'Ticket asignado',
        details: 'Ticket #1001 asignado a Agente1',
        type: 'assign',
        icon: 'bi-person-check',
        color: '#0dcaf0'
    },
    {
        id: 3,
        timestamp: '2025-12-17 10:35:48',
        user: 'Agente1',
        action: 'Estado modificado',
        details: 'Estado cambiado de "Pendiente" a "En Proceso"',
        type: 'update',
        icon: 'bi-arrow-repeat',
        color: '#fd7e14'
    }
];

function loadAuditLog() {
    const container = document.getElementById('auditLogList');
    if (!container) return;
    
    if (auditLogs.length === 0) {
        container.innerHTML = '<div class="text-center py-4 text-muted">No hay registros de auditoría</div>';
        return;
    }
    
    container.innerHTML = auditLogs.map(log => `
        <div class="audit-log-item">
            <div class="audit-log-icon" style="background-color: ${log.color}20; color: ${log.color};">
                <i class="bi ${log.icon}"></i>
            </div>
            <div class="audit-log-content">
                <div class="audit-log-header">
                    <span class="audit-log-action">${log.action}</span>
                    <span class="audit-log-timestamp">${log.timestamp}</span>
                </div>
                <div class="audit-log-details">${log.details}</div>
                <div class="audit-log-user">Por: ${log.user}</div>
            </div>
        </div>
    `).join('');
}

function filterAuditLog(type) {
    // Implementar filtrado por tipo de acción
    console.log('Filtrando por:', type);
}

// ============================================
// ROLES Y PERMISOS
// ============================================

const roles = [
    {
        id: 1,
        name: 'Administrador',
        description: 'Acceso completo al sistema',
        permissions: ['all'],
        userCount: 2,
        color: '#dc3545'
    },
        {
        id: 2,
        name: 'Supervisor',
        description: 'Supervisión y reportes avanzados',
        permissions: ['tickets.view', 'tickets.assign', 'reports.view', 'reports.advanced'],
        userCount: 3,
        color: '#6f42c1'
    },
    {
        id: 3,
        name: 'Agente',
        description: 'Puede gestionar tickets asignados',
        permissions: ['tickets.view', 'tickets.edit'],
        userCount: 12,
        color: '#198754'
    }
];

function loadRoles() {
    const container = document.getElementById('rolesList');
    if (!container) return;
    
    container.innerHTML = roles.map(role => `
        <div class="role-card">
            <div class="role-header">
                <div class="role-icon" style="background-color: ${role.color}20; color: ${role.color};">
                    <i class="bi bi-shield-fill"></i>
                </div>
                <div class="role-info">
                    <h5 class="role-name">${role.name}</h5>
                    <p class="role-description">${role.description}</p>
                </div>
            </div>
            <div class="role-stats">
                <div class="role-stat">
                    <i class="bi bi-people-fill"></i>
                    <span>${role.userCount} usuarios</span>
                </div>
                <div class="role-stat">
                    <i class="bi bi-key-fill"></i>
                    <span>${role.permissions.includes('all') ? 'Todos' : role.permissions.length} permisos</span>
                </div>
            </div>
            <div class="role-actions">
                <button class="btn btn-sm btn-outline-primary" onclick="editRole(${role.id})">
                    <i class="bi bi-pencil"></i> Editar
                </button>
                <button class="btn btn-sm btn-outline-info" onclick="viewRoleDetails(${role.id})">
                    <i class="bi bi-eye"></i> Ver detalles
                </button>
            </div>
        </div>
    `).join('');
}

function editRole(roleId) {
    console.log('Editando rol:', roleId);
    showToast('Info', 'Función en desarrollo - Backend requerido', 'info');
}

function viewRoleDetails(roleId) {
    const role = roles.find(r => r.id === roleId);
    if (!role) return;
    
    // Mostrar modal con detalles del rol
    showToast('Detalles del Rol', `${role.name}: ${role.description}`, 'info');
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Cargar notificaciones
    loadNotifications();
    
    // Inicializar sistema de tags
    initializeTags();
    
    // Cargar audit log si estamos en esa vista
    if (document.getElementById('auditLogList')) {
        loadAuditLog();
    }
    
    // Cargar roles si estamos en esa vista
    if (document.getElementById('rolesList')) {
        loadRoles();
    }
    
    // Simular notificaciones en tiempo real (solo para demo)
    // Comentar en producción
    // simulateRealTimeNotifications();
    
    // Soporte de logo compacto eliminado: ya no se inicializa fallback.
});
// Nota: la función `forceCompactLogoFallback` fue eliminada.
