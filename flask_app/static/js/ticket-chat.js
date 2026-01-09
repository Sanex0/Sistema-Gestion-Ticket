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

// Estado del modal de previsualización
window._adjuntoPreview = window._adjuntoPreview || {
    idAdj: null,
    nomAdj: null,
    url: null,
    blob: null,
    contentType: null
};

// Estado de adjuntos seleccionados en el chat (para poder quitar con X)
window.chatAttachmentsState = window.chatAttachmentsState || {
    desktop: [],
    mobile: []
};

function _formatBytes(bytes) {
    const n = Number(bytes || 0);
    if (!Number.isFinite(n) || n <= 0) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = n;
    let idx = 0;
    while (size >= 1024 && idx < units.length - 1) {
        size /= 1024;
        idx++;
    }
    const decimals = idx === 0 ? 0 : (idx === 1 ? 0 : 1);
    return `${size.toFixed(decimals)} ${units[idx]}`;
}

function _ensureFilenameWithOriginalExt(filename, originalName) {
    const name = String(filename || '').trim();
    if (!name) return '';
    const orig = String(originalName || '').trim();
    const origExt = orig.includes('.') ? orig.split('.').pop() : '';
    const hasExt = name.includes('.') && name.split('.').pop().length > 0;
    if (hasExt) return name;
    if (origExt) return `${name}.${origExt}`;
    return name;
}

function _escapeForOnclickSingleQuotedString(value) {
    return String(value ?? '')
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/\r?\n/g, ' ');
}

function _buildAdjuntoDownloadUrl(idAdj) {
    return '/api/adjuntos/' + idAdj + '/download';
}

function _getAbsoluteUrl(path) {
    const p = String(path || '');
    try {
        // En algunos contextos (file://) origin puede ser 'null'
        const hasHost = !!(window.location && window.location.host);
        const base = hasHost ? (window.location.protocol + '//' + window.location.host) : '';
        if (!base) return p;
        return base + p;
    } catch (e) {
        return p;
    }
}

async function _copyToClipboard(text) {
    const value = String(text || '');
    if (!value) return false;

    // Intento 1: Clipboard API
    try {
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            await navigator.clipboard.writeText(value);
            return true;
        }
    } catch (e) {
        // fallback
    }

    // Intento 2: textarea + execCommand (fallback para HTTP / permisos)
    try {
        const ta = document.createElement('textarea');
        ta.value = value;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.top = '-9999px';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        const ok = document.execCommand && document.execCommand('copy');
        ta.remove();
        return !!ok;
    } catch (e2) {
        return false;
    }
}

async function _fetchAdjuntoBlob(idAdj) {
    const url = _buildAdjuntoDownloadUrl(idAdj);
    const res = await fetch(url, { method: 'GET' });
    if (!res.ok) {
        throw new Error('No se pudo obtener el adjunto');
    }
    const contentType = res.headers.get('Content-Type') || '';
    const blob = await res.blob();
    return { blob, contentType, url };
}

function _renderAdjuntoPreviewInto(container, objectUrl, contentType, filename) {
    const ct = String(contentType || '').toLowerCase();
    const lower = String(filename || '').toLowerCase();
    const isImage = ct.startsWith('image/') || lower.match(/\.(png|jpg|jpeg|gif|webp|bmp|svg)$/);
    const isPdf = ct.includes('pdf') || lower.endsWith('.pdf');
    const isText = ct.startsWith('text/') || lower.match(/\.(txt|log|md|csv)$/);

    if (isImage) {
        container.innerHTML = '';
        const img = document.createElement('img');
        img.src = objectUrl;
        img.alt = filename || 'Adjunto';
        img.className = 'img-fluid rounded-3 border';
        img.style.maxHeight = '70vh';
        img.style.display = 'block';
        img.style.margin = '0 auto';
        container.appendChild(img);
        return;
    }

    if (isPdf) {
        container.innerHTML = '<iframe title="Vista previa" src="' + objectUrl + '" style="width: 100%; height: 70vh; border: 0;"></iframe>';
        return;
    }

    if (isText) {
        container.innerHTML = '<div class="d-flex align-items-center justify-content-center text-muted" style="min-height: 70vh;"><div class="text-center"><div class="spinner-border" role="status" aria-hidden="true"></div><div class="mt-2">Cargando contenido...</div></div></div>';
        return 'text';
    }

    const icon = _getFileIconClassByName(filename);
    container.innerHTML =
        '<div class="d-flex align-items-center justify-content-center" style="min-height: 70vh;">' +
            '<div class="text-center">' +
                '<div class="mb-2"><i class="' + icon + '" style="font-size: 3rem; opacity: 0.4;"></i></div>' +
                '<div class="fw-semibold">Sin vista previa</div>' +
                '<div class="text-muted small">Puedes descargar el archivo para verlo.</div>' +
            '</div>' +
        '</div>';
    return;
}

function _getAdjuntoPreviewModal() {
    const el = document.getElementById('adjuntoPreviewModal');
    if (!el || !window.bootstrap || !bootstrap.Modal) return null;
    return bootstrap.Modal.getOrCreateInstance(el);
}

function _cleanupAdjuntoPreview() {
    try {
        if (window._adjuntoPreview && window._adjuntoPreview.url) {
            URL.revokeObjectURL(window._adjuntoPreview.url);
        }
    } catch (e) {
        // noop
    }
    window._adjuntoPreview = { idAdj: null, nomAdj: null, url: null, blob: null, contentType: null };
}

window.openAdjuntoPreview = async function(idAdj, nomAdj) {
    try {
        const modal = _getAdjuntoPreviewModal();
        if (!modal) {
            showToast('❌ No se pudo abrir el visor de adjuntos', 'warning');
            return;
        }

        const title = document.getElementById('adjuntoPreviewTitle');
        const meta = document.getElementById('adjuntoPreviewMeta');
        const body = document.getElementById('adjuntoPreviewBody');
        const iconEl = document.getElementById('adjuntoPreviewIcon');
        const btnShare = document.getElementById('adjuntoPreviewBtnShare');
        const btnCopyLink = document.getElementById('adjuntoPreviewBtnCopyLink');
        const btnDownload = document.getElementById('adjuntoPreviewBtnDownload');
        const btnOpenTab = document.getElementById('adjuntoPreviewBtnOpenTab');

        if (!body) return;

        // Reset UI
        if (title) title.textContent = nomAdj || 'Adjunto';
        if (meta) meta.textContent = 'Cargando vista previa...';
        if (iconEl) {
            const iconClass = _getFileIconClassByName(nomAdj);
            iconEl.className = iconClass + ' text-muted';
        }
        body.innerHTML = '<div class="d-flex align-items-center justify-content-center text-muted" style="min-height: 55vh;">' +
            '<div class="text-center"><div class="spinner-border" role="status" aria-hidden="true"></div><div class="mt-2">Cargando vista previa...</div></div>' +
        '</div>';

        // Bind acciones
        const downloadUrl = _buildAdjuntoDownloadUrl(idAdj);
        const fullUrl = _getAbsoluteUrl(downloadUrl);
        if (btnOpenTab) {
            btnOpenTab.onclick = function() {
                window.open(downloadUrl, '_blank', 'noopener');
            };
        }
        if (btnShare) {
            btnShare.onclick = async function() {
                try {
                    if (navigator.share) {
                        await navigator.share({ title: nomAdj || 'Adjunto', url: fullUrl });
                        return;
                    }
                } catch (e) {
                    // fallback to clipboard
                }
                const ok = await _copyToClipboard(fullUrl);
                if (ok) {
                    showToast('✅ Enlace copiado', 'success');
                } else {
                    prompt('Copia el enlace:', fullUrl);
                }
            };
        }
        if (btnCopyLink) {
            btnCopyLink.onclick = async function() {
                const ok = await _copyToClipboard(fullUrl);
                if (ok) {
                    showToast('✅ Enlace copiado', 'success');
                } else {
                    prompt('Copia el enlace:', fullUrl);
                }
            };
        }
        if (btnDownload) {
            btnDownload.onclick = function() {
                window.guardarAdjuntoComo(idAdj, nomAdj);
            };
        }

        // Abrir modal (rápido) mientras carga
        modal.show();

        // Limpieza al cerrar
        const modalEl = document.getElementById('adjuntoPreviewModal');
        if (modalEl && !modalEl.dataset.boundCleanup) {
            modalEl.dataset.boundCleanup = '1';
            modalEl.addEventListener('hidden.bs.modal', function() {
                _cleanupAdjuntoPreview();
            });
        }

        // Cargar blob
        _cleanupAdjuntoPreview();
        const fetched = await _fetchAdjuntoBlob(idAdj);
        const objectUrl = URL.createObjectURL(fetched.blob);
        window._adjuntoPreview = { idAdj, nomAdj, url: objectUrl, blob: fetched.blob, contentType: fetched.contentType };

        const sizeText = _formatBytes(fetched.blob && fetched.blob.size);
        const ext = (String(nomAdj || '').includes('.') ? String(nomAdj).split('.').pop().toUpperCase() : '') || '';
        if (meta) meta.textContent = [ext, sizeText].filter(Boolean).join(' · ') || 'Adjunto';

        const mode = _renderAdjuntoPreviewInto(body, objectUrl, fetched.contentType, nomAdj);
        if (mode === 'text') {
            // Renderizar texto
            const text = await fetched.blob.text();
            const maxChars = 200000;
            const safe = escapeHtml(text.length > maxChars ? (text.slice(0, maxChars) + '\n\n... (truncado)') : text);
            body.innerHTML = '<pre class="bg-light border rounded-3 p-3 small" style="max-height: 70vh; overflow: auto; white-space: pre-wrap;">' + safe + '</pre>';
        }
    } catch (e) {
        console.error('openAdjuntoPreview error:', e);
        showToast('❌ No se pudo previsualizar el adjunto', 'warning');
    }
};

window.guardarAdjuntoComo = async function(idAdj, nomAdj) {
    try {
        const original = nomAdj || 'archivo';
        const suggested = original;
        const nuevoNombreInput = prompt('Nombre de archivo:', suggested);
        if (nuevoNombreInput === null) return; // cancel
        const nuevoNombre = _ensureFilenameWithOriginalExt(nuevoNombreInput, original);
        if (!nuevoNombre) {
            showToast('⚠️ Nombre inválido', 'warning');
            return;
        }

        // Reusar blob del preview si aplica
        let blob = null;
        if (window._adjuntoPreview && window._adjuntoPreview.idAdj === idAdj && window._adjuntoPreview.blob) {
            blob = window._adjuntoPreview.blob;
        } else {
            const fetched = await _fetchAdjuntoBlob(idAdj);
            blob = fetched.blob;
        }

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nuevoNombre;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
    } catch (e) {
        console.error('guardarAdjuntoComo error:', e);
        showToast('❌ No se pudo descargar el adjunto', 'warning');
    }
};

function _getFileIconClassByName(name) {
    const lower = String(name || '').toLowerCase();
    if (lower.match(/\.(png|jpg|jpeg|gif|webp|bmp|svg)$/)) return 'bi bi-image';
    if (lower.match(/\.(pdf)$/)) return 'bi bi-file-earmark-pdf';
    if (lower.match(/\.(txt|log|md)$/)) return 'bi bi-file-earmark-text';
    if (lower.match(/\.(doc|docx)$/)) return 'bi bi-file-earmark-word';
    if (lower.match(/\.(xls|xlsx|csv)$/)) return 'bi bi-file-earmark-excel';
    if (lower.match(/\.(zip|rar|7z)$/)) return 'bi bi-file-earmark-zip';
    return 'bi bi-file-earmark';
}

function _getChatScope() {
    // Preferir el input visible; si ambos están, devolver desktop por default
    const desktopInput = document.getElementById('chatMessageInputDesktop');
    if (desktopInput && desktopInput.offsetParent !== null) return 'desktop';
    return 'mobile';
}

function _getChatAttachments(scope) {
    const s = scope === 'desktop' ? 'desktop' : 'mobile';
    return (window.chatAttachmentsState && Array.isArray(window.chatAttachmentsState[s]))
        ? window.chatAttachmentsState[s]
        : [];
}

function _setChatAttachments(scope, list) {
    const s = scope === 'desktop' ? 'desktop' : 'mobile';
    if (!window.chatAttachmentsState) window.chatAttachmentsState = { desktop: [], mobile: [] };
    window.chatAttachmentsState[s] = Array.isArray(list) ? list : [];
}

function _renderChatAttachmentsBar(scope) {
    const s = scope === 'desktop' ? 'desktop' : 'mobile';
    const barId = s === 'desktop' ? 'chatAttachmentsBarDesktop' : 'chatAttachmentsBarMobile';
    const listId = s === 'desktop' ? 'chatAttachmentsListDesktop' : 'chatAttachmentsListMobile';

    const bar = document.getElementById(barId);
    const listEl = document.getElementById(listId);
    if (!bar || !listEl) return;

    const items = _getChatAttachments(s);
    if (!items || items.length === 0) {
        bar.classList.add('d-none');
        listEl.innerHTML = '';
        return;
    }

    bar.classList.remove('d-none');
    listEl.innerHTML = items.map((it, idx) => {
        const f = it && it.file;
        const name = f ? f.name : 'archivo';
        const size = f ? _formatBytes(f.size) : '';
        const icon = _getFileIconClassByName(name);
        const status = (it && it.status) || 'ready';
        const isUploading = status === 'uploading';
        const isError = status === 'error';

        const statusHtml = isUploading
            ? '<span class="ms-2 small text-muted"><span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Subiendo...</span>'
            : (isError ? '<span class="ms-2 small text-danger">Error</span>' : '');

        const removeDisabled = isUploading ? 'disabled' : '';
        const removeTitle = isUploading ? 'Subiendo...' : 'Quitar';

        return (
            '<div class="border rounded-3 bg-light px-2 py-2 d-flex align-items-center" style="max-width: 100%;">' +
                '<i class="' + icon + ' me-2 text-muted"></i>' +
                '<div class="d-flex flex-column" style="min-width: 0;">' +
                    '<div class="small fw-semibold text-truncate" style="max-width: 220px;">' + escapeHtml(name) + '</div>' +
                    (size ? '<div class="small text-muted">' + escapeHtml(size) + '</div>' : '') +
                '</div>' +
                statusHtml +
                '<button class="btn btn-link p-0 ms-2" type="button" ' + removeDisabled + ' title="' + removeTitle + '" onclick="window.removeChatAttachment(\'' + s + '\',' + idx + ')">' +
                    '<i class="bi bi-x-lg text-muted"></i>' +
                '</button>' +
            '</div>'
        );
    }).join('');
}

window.removeChatAttachment = function(scope, index) {
    try {
        const items = _getChatAttachments(scope).slice();
        if (index < 0 || index >= items.length) return;
        const it = items[index];
        if (it && it.status === 'uploading') return;
        items.splice(index, 1);
        _setChatAttachments(scope, items);
        _renderChatAttachmentsBar(scope);
    } catch (e) {
        // noop
    }
};

function _addChatFiles(scope, fileList) {
    const files = Array.from(fileList || []).filter(Boolean);
    if (files.length === 0) return;

    const current = _getChatAttachments(scope);
    const dedup = new Map();
    for (const it of current) {
        const f = it && it.file;
        if (!f) continue;
        const key = `${f.name || ''}|${f.size || ''}|${f.lastModified || ''}`;
        dedup.set(key, it);
    }
    for (const f of files) {
        const key = `${f.name || ''}|${f.size || ''}|${f.lastModified || ''}`;
        if (!dedup.has(key)) dedup.set(key, { file: f, status: 'ready' });
    }

    _setChatAttachments(scope, Array.from(dedup.values()));
    _renderChatAttachmentsBar(scope);
}

function _getAllChatPendingFiles() {
    // Combina desktop + mobile (por si ambos existen), deduplicando
    const all = [];
    for (const s of ['desktop', 'mobile']) {
        for (const it of _getChatAttachments(s)) {
            if (it && it.file) all.push(it.file);
        }
    }
    const dedup = new Map();
    for (const f of all) {
        const key = `${f.name || ''}|${f.size || ''}|${f.lastModified || ''}`;
        if (!dedup.has(key)) dedup.set(key, f);
    }
    return Array.from(dedup.values());
}

function _clearChatAttachmentsIfAllSucceeded() {
    const anyError = ['desktop', 'mobile'].some(s => _getChatAttachments(s).some(it => it && it.status === 'error'));
    const anyUploading = ['desktop', 'mobile'].some(s => _getChatAttachments(s).some(it => it && it.status === 'uploading'));
    if (anyUploading) return;
    if (anyError) {
        // Mantener los fallidos para que el usuario pueda quitarlos o reintentar enviando
        _renderChatAttachmentsBar('desktop');
        _renderChatAttachmentsBar('mobile');
        return;
    }
    _setChatAttachments('desktop', []);
    _setChatAttachments('mobile', []);
    _renderChatAttachmentsBar('desktop');
    _renderChatAttachmentsBar('mobile');
}

// Inicializar listeners de adjuntos del chat
document.addEventListener('DOMContentLoaded', function() {
    try {
        const inputDesktop = document.getElementById('fileAttachmentDesktop');
        if (inputDesktop && !inputDesktop.dataset.boundAttachments) {
            inputDesktop.dataset.boundAttachments = '1';
            inputDesktop.addEventListener('change', function(e) {
                _addChatFiles('desktop', e.target.files);
                // limpiar para permitir re-seleccionar el mismo archivo
                e.target.value = '';
            });
        }
        const inputMobile = document.getElementById('fileAttachment');
        if (inputMobile && !inputMobile.dataset.boundAttachments) {
            inputMobile.dataset.boundAttachments = '1';
            inputMobile.addEventListener('change', function(e) {
                _addChatFiles('mobile', e.target.files);
                e.target.value = '';
            });
        }

        // Render inicial por si hay estado previo
        _renderChatAttachmentsBar('desktop');
        _renderChatAttachmentsBar('mobile');
    } catch (e) {
        // noop
    }
});

function escapeHtml(text) {
    return String(text ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function obtenerAdjuntosPorMensaje(mensajeId) {
    try {
        const data = await apiRequest(`/mensajes/${mensajeId}/adjuntos`);
        if (data && data.success && Array.isArray(data.adjuntos)) return data.adjuntos;
        return [];
    } catch (e) {
        return [];
    }
}

async function enriquecerMensajesConAdjuntos(mensajes) {
    if (!Array.isArray(mensajes) || mensajes.length === 0) return mensajes;

    const needs = mensajes.filter(m => {
        if (!m) return false;
        const n = Number(m.total_adjuntos ?? 0);
        return Number.isFinite(n) && n > 0;
    });
    if (needs.length === 0) return mensajes;

    const adjuntosMap = new Map();
    await Promise.all(needs.map(async m => {
        const mid = m.id_msg;
        if (!mid) return;
        const adj = await obtenerAdjuntosPorMensaje(mid);
        adjuntosMap.set(mid, adj);
    }));

    return mensajes.map(m => {
        const mid = m && m.id_msg;
        if (!mid) return m;
        const adj = adjuntosMap.get(mid);
        if (Array.isArray(adj)) {
            return { ...m, adjuntos: adj };
        }
        return m;
    });
}

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
            // Subir adjuntos (si existen) asociados al mensaje inicial del ticket
            try {
                var idMsgInicial = result.id_msg_inicial || result.id_msg_inicial === 0 ? result.id_msg_inicial : null;
                // Tomar archivos desde features.js (attachedFiles) y/o desde el preview del dashboard (selectedFiles)
                var filesToUpload = [];
                if (typeof attachedFiles !== 'undefined' && attachedFiles && attachedFiles.length > 0) {
                    for (const f of attachedFiles) {
                        if (f && f.file) filesToUpload.push(f.file);
                    }
                }
                if (typeof selectedFiles !== 'undefined' && selectedFiles && selectedFiles.length > 0) {
                    for (const f of selectedFiles) {
                        if (f) filesToUpload.push(f);
                    }
                }

                // Deduplicar por nombre+tamaño+lastModified
                var dedup = new Map();
                for (const f of filesToUpload) {
                    try {
                        const key = `${f.name || ''}|${f.size || ''}|${f.lastModified || ''}`;
                        if (!dedup.has(key)) dedup.set(key, f);
                    } catch (e) {
                        // noop
                    }
                }
                filesToUpload = Array.from(dedup.values());

                if (idMsgInicial && filesToUpload.length > 0) {
                    let okCount = 0;
                    let failCount = 0;
                    for (const fileToUpload of filesToUpload) {
                        if (!fileToUpload) continue;
                        const up = await DashboardAPI.subirAdjuntoMensaje(idMsgInicial, fileToUpload);
                        if (!up || !up.success) {
                            failCount++;
                            const msg = (up && (up.error || up.mensaje || up.message)) || 'No se pudo subir el archivo';
                            console.warn('No se pudo subir adjunto:', up);
                            showToast('❌ ' + msg, 'warning');
                        } else {
                            okCount++;
                        }
                    }

                    if (okCount > 0) {
                        showToast(`📎 ${okCount} adjunto(s) subido(s)`, 'success');
                    }
                    if (failCount > 0 && okCount === 0) {
                        showToast('❌ No se pudo subir ningún adjunto', 'warning');
                    }
                }
            } catch (e) {
                console.warn('Error subiendo adjuntos del ticket:', e);
                showToast('❌ Error subiendo adjuntos', 'warning');
            }

            showToast('✅ Ticket creado correctamente', 'success');
            
            var modal = bootstrap.Modal.getInstance(document.getElementById('newTicketModal'));
            if (modal) modal.hide();
            
            form.reset();
            
            var attachmentList = document.getElementById('attachmentList');
            var attachmentCount = document.getElementById('attachmentCount');
            if (attachmentList) attachmentList.innerHTML = '';
            if (attachmentCount) attachmentCount.textContent = '0';

            // Reset del estado interno del uploader
            try {
                if (typeof attachedFiles !== 'undefined') attachedFiles = [];
                if (typeof selectedFiles !== 'undefined') selectedFiles = [];
                var fileInput = document.getElementById('ticketAttachments');
                if (fileInput) fileInput.value = '';
            } catch (e) {
                // noop
            }
            
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

            // Cargar adjuntos para mensajes que reportan total_adjuntos
            try {
                result.data = await enriquecerMensajesConAdjuntos(result.data);
            } catch (e) {
                console.warn('[cargarMensajes] No se pudieron enriquecer adjuntos:', e);
            }
            
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

            // Si cambió la cantidad de adjuntos (mismo largo, mismos ids), también re-render
            if (!hayNuevos && window.chatMessages.length > 0 && result.data.length === window.chatMessages.length) {
                try {
                    const prevById = new Map(window.chatMessages.map(m => [m.id_msg, m]));
                    for (const m of result.data) {
                        const prev = prevById.get(m.id_msg);
                        const prevTotal = prev ? (prev.total_adjuntos || 0) : 0;
                        const newTotal = m ? (m.total_adjuntos || 0) : 0;
                        if (String(prevTotal) !== String(newTotal)) {
                            hayNuevos = true;
                            console.log('[cargarMensajes] Cambio en adjuntos detectado en msg ' + m.id_msg + ': ' + prevTotal + ' -> ' + newTotal);
                            break;
                        }
                    }
                } catch (e) {
                    // noop
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
    
    const contenido = String(msg.contenido || '').trim();
    const hasAdjuntos = !!(msg.adjuntos && Array.isArray(msg.adjuntos) && msg.adjuntos.length > 0);
    const esPlaceholderAdjuntos = hasAdjuntos && (!contenido || contenido.toLowerCase() === 'adjuntos');
    const contenidoHtml = esPlaceholderAdjuntos ? '' : ('<p class="mb-1">' + escapeHtml(contenido) + '</p>');

    let adjuntosHtml = '';
    if (hasAdjuntos) {
        const cards = msg.adjuntos.map(a => {
            const idAdj = a && a.id_adj;
            const nom = (a && a.nom_adj) ? a.nom_adj : 'archivo';
            const ext = (a && a.ext) ? String(a.ext).toUpperCase() : (String(nom).includes('.') ? String(nom).split('.').pop().toUpperCase() : 'ARCHIVO');
            const size = (a && a.size_bytes) ? _formatBytes(a.size_bytes) : '';
            const meta = [ext, size].filter(Boolean).join(' · ');
            const icon = _getFileIconClassByName(nom);
            const url = _buildAdjuntoDownloadUrl(idAdj);
            const nomSafe = _escapeForOnclickSingleQuotedString(nom);

            return (
                '<div class="bg-white text-dark rounded-3 border overflow-hidden">' +
                    '<div class="d-flex align-items-center p-2">' +
                        '<div class="bg-light rounded-2 d-flex align-items-center justify-content-center me-2" style="width: 40px; height: 40px; flex: 0 0 40px;">' +
                            '<i class="' + icon + ' text-muted"></i>' +
                        '</div>' +
                        '<div class="d-flex flex-column" style="min-width: 0;">' +
                            '<div class="small fw-semibold text-truncate" style="max-width: 260px;">' + escapeHtml(nom) + '</div>' +
                            (meta ? '<div class="small text-muted">' + escapeHtml(meta) + '</div>' : '') +
                        '</div>' +
                    '</div>' +
                    '<div class="d-flex border-top">' +
                        '<button type="button" class="btn btn-link flex-fill text-center small fw-semibold py-2 text-decoration-none" onclick="window.openAdjuntoPreview(' + idAdj + ', \'' + nomSafe + '\')">Abrir</button>' +
                        '<button type="button" class="btn btn-link flex-fill text-center small fw-semibold py-2 text-decoration-none border-start" onclick="window.guardarAdjuntoComo(' + idAdj + ', \'' + nomSafe + '\')">Guardar como...</button>' +
                    '</div>' +
                '</div>'
            );
        }).join('');

        adjuntosHtml = '<div class="mt-2 d-grid gap-2">' + cards + '</div>';
    }

    if (esMensajePropio) {
        return '<div class="message-wrapper message-right" data-msg-id="' + msg.id_msg + '">' +
            '<div class="message-content">' +
            '<div class="message-bubble message-bubble-right">' +
            '<div class="message-sender">Tú (' + nombreRemitente + ')</div>' +
            contenidoHtml +
            adjuntosHtml +
            '<small class="message-time">' + hora + '</small>' +
            '</div></div></div>';
    } else {
        var tipoLabel = msg.remitente_tipo === 'Usuario' ? 'Usuario Externo' : 'Operador';
        return '<div class="message-wrapper message-left" data-msg-id="' + msg.id_msg + '">' +
            '<div class="message-content">' +
            '<div class="message-bubble message-bubble-left">' +
            '<div class="message-sender">' + nombreRemitente + ' (' + tipoLabel + ')</div>' +
            contenidoHtml +
            adjuntosHtml +
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

    // Si no hay texto pero hay adjuntos seleccionados, permitir envío como "mensaje de adjuntos"
    try {
        var hasFiles = _getAllChatPendingFiles().length > 0;
        if ((!mensaje || !mensaje.trim()) && hasFiles) {
            mensaje = 'Adjuntos';
        }
    } catch (e) {
        // noop
    }
    
    if (!mensaje || !mensaje.trim()) {
        showToast('⚠️ Escribe un mensaje o adjunta un archivo antes de enviar', 'warning');
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
            // Si hay archivos seleccionados en el chat, subirlos y asociarlos a este mensaje
            try {
                var mensajeId = result && result.data ? result.data.id_msg : null;
                var fileInputDesktop = document.getElementById('fileAttachmentDesktop');
                var fileInputMobile = document.getElementById('fileAttachment');
                var files = _getAllChatPendingFiles();

                if (mensajeId && files.length > 0) {
                    // Marcar estado "subiendo" en la barra
                    try {
                        for (const s of ['desktop', 'mobile']) {
                            const items = _getChatAttachments(s).map(it => ({ ...it, status: 'uploading' }));
                            _setChatAttachments(s, items);
                            _renderChatAttachmentsBar(s);
                        }
                    } catch (e) {
                        // noop
                    }

                    let okCount = 0;
                    let failCount = 0;
                    for (const file of files) {
                        const up = await DashboardAPI.subirAdjuntoMensaje(mensajeId, file);
                        if (!up || !up.success) {
                            failCount++;
                            const msg = (up && (up.error || up.mensaje || up.message)) || `No se pudo subir ${file.name}`;
                            console.warn('No se pudo subir adjunto:', up);
                            showToast('❌ ' + msg, 'warning');

                            // Marcar error (si sigue en la lista)
                            try {
                                for (const s of ['desktop', 'mobile']) {
                                    const items = _getChatAttachments(s).map(it => {
                                        if (!it || !it.file) return it;
                                        const key = `${it.file.name || ''}|${it.file.size || ''}|${it.file.lastModified || ''}`;
                                        const fkey = `${file.name || ''}|${file.size || ''}|${file.lastModified || ''}`;
                                        if (key === fkey) return { ...it, status: 'error' };
                                        return it;
                                    });
                                    _setChatAttachments(s, items);
                                    _renderChatAttachmentsBar(s);
                                }
                            } catch (e) {
                                // noop
                            }
                        } else {
                            okCount++;

                            // Marcar done (si sigue en la lista)
                            try {
                                for (const s of ['desktop', 'mobile']) {
                                    const items = _getChatAttachments(s).map(it => {
                                        if (!it || !it.file) return it;
                                        const key = `${it.file.name || ''}|${it.file.size || ''}|${it.file.lastModified || ''}`;
                                        const fkey = `${file.name || ''}|${file.size || ''}|${file.lastModified || ''}`;
                                        if (key === fkey) return { ...it, status: 'done' };
                                        return it;
                                    });
                                    _setChatAttachments(s, items);
                                    _renderChatAttachmentsBar(s);
                                }
                            } catch (e) {
                                // noop
                            }
                        }
                    }

                    if (okCount > 0) {
                        showToast(`📎 ${okCount} adjunto(s) subido(s)`, 'success');
                    }
                    if (failCount > 0 && okCount === 0) {
                        showToast('❌ No se pudo subir ningún adjunto', 'warning');
                    }
                }

                // Reset inputs (los dejamos limpios siempre; la barra maneja el estado)
                if (fileInputDesktop) fileInputDesktop.value = '';
                if (fileInputMobile) fileInputMobile.value = '';

                // Si todo ok, limpiar barra; si hubo error, mantener para reintento o quitar con X
                try {
                    _clearChatAttachmentsIfAllSucceeded();
                } catch (e) {
                    // noop
                }

                // Refrescar adjuntos del ticket en el offcanvas (si existe)
                try {
                    if (window.currentTicketId && typeof cargarAdjuntosTicket === 'function') {
                        cargarAdjuntosTicket(window.currentTicketId);
                    }
                } catch (e) {
                    // noop
                }
            } catch (e) {
                console.warn('Error subiendo adjuntos del mensaje:', e);
                showToast('❌ Error subiendo adjuntos', 'warning');

                // Salir de modo uploading para permitir quitar o reintentar
                try {
                    for (const s of ['desktop', 'mobile']) {
                        const items = _getChatAttachments(s).map(it => ({ ...it, status: 'error' }));
                        _setChatAttachments(s, items);
                        _renderChatAttachmentsBar(s);
                    }
                } catch (e2) {
                    // noop
                }
            }

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
