-- ============================================
-- DATOS INICIALES PARA SISTEMA DE TICKETS
-- ============================================

USE sistema_ticket_recrear;

-- ============================================
-- 1. ESTADOS
-- ============================================
INSERT INTO ESTADO (descripcion) VALUES 
('Nuevo'),
('En Proceso'),
('Resuelto'),
('Cerrado'),
('Pendiente'),
('Sin responder');

-- ============================================
-- 2. PRIORIDADES
-- ============================================
INSERT INTO PRIORIDAD (jerarquia, descripcion) VALUES 
(1, 'Urgente'),
(2, 'Alta'),
(3, 'Media'),
(4, 'Baja');

-- ============================================
-- 3. CLUBES
-- ============================================
INSERT INTO CLUB (nom_club) VALUES 
('ADM'),
('CAM'),
('CDR'),
('CALF'),
('CALC');

-- ============================================
-- 4. SLA (Service Level Agreements)
-- ============================================
INSERT INTO SLA (nombre, tiempo_primera_respuesta_min, tiempo_resolucion_min, activo) VALUES 
('SLA Estándar', 60, 480, 1),
('SLA Premium', 30, 240, 1),
('SLA VIP', 15, 120, 1),
('SLA Básico', 120, 720, 1);

-- ============================================
-- 5. ROLES GLOBALES
-- ============================================
INSERT INTO ROL_GLOBAL (nombre, activo) VALUES 
('Admin', 1),
('Supervisor', 1),
('Agente', 1);

-- ============================================
-- 6. CANALES
-- ============================================
INSERT INTO CANAL (id_canal, nombre) VALUES 
(1, 'Email'),
(2, 'Web'),
(3, 'Teléfono'),
(4, 'WhatsApp'),
(5, 'Chat');

-- ============================================
-- 7. OPERADORES DE PRUEBA
-- ============================================
-- Nota: Las contraseñas deben ser hasheadas en producción
INSERT INTO OPERADOR (email, nombre, telefono, estado, id_rol_global) VALUES 
('admin@recrear.cl', 'Administrador Sistema', '+56912345678', 1, 1),
('supervisor@recrear.cl', 'Supervisor Principal', '+56912345679', 1, 2),
('agente1@recrear.cl', 'Agente Uno', '+56912345680', 1, 3),
('agente2@recrear.cl', 'Agente Dos', '+56912345681', 1, 3);

-- ============================================
-- 8. USUARIOS EXTERNOS DE PRUEBA
-- ============================================
INSERT INTO USUARIO_EXT (rut, nombre, telefono, email, existe_flex) VALUES 
('12345678-9', 'Juan Pérez', '+56987654321', 'juan.perez@email.com', 0),
('98765432-1', 'María González', '+56987654322', 'maria.gonzalez@email.com', 0),
('11223344-5', 'Pedro Rodríguez', '+56987654323', 'pedro.rodriguez@email.com', 0);

-- ============================================
-- 9. DEPARTAMENTOS
-- ============================================
INSERT INTO DEPARTAMENTO (descripcion, email, operador_default, recibe_externo) VALUES 
('Soporte Técnico', 'soporte@recrear.cl', 3, 1),
('Atención al Cliente', 'atencion@recrear.cl', 4, 1),
('Administración', 'admin@recrear.cl', 1, 0);

-- ============================================
-- 10. PERMISOS
-- ============================================
INSERT INTO PERMISO (codigo, descripcion, activo) VALUES 
('ticket.create', 'Crear tickets', 1),
('ticket.read', 'Ver tickets', 1),
('ticket.update', 'Actualizar tickets', 1),
('ticket.delete', 'Eliminar tickets', 1),
('ticket.assign', 'Asignar tickets', 1),
('operador.create', 'Crear operadores', 1),
('operador.read', 'Ver operadores', 1),
('operador.update', 'Actualizar operadores', 1),
('operador.delete', 'Eliminar operadores', 1),
('config.manage', 'Gestionar configuración', 1);

-- ============================================
-- 11. ASIGNAR PERMISOS A ROLES
-- ============================================
-- Admin: todos los permisos
INSERT INTO ROL_PERMISO (id_rol, id_permiso) 
SELECT 1, id_permiso FROM PERMISO WHERE activo = 1;

-- Supervisor: permisos de tickets y lectura de operadores
INSERT INTO ROL_PERMISO (id_rol, id_permiso) VALUES 
(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 7);

-- Agente: permisos básicos de tickets
INSERT INTO ROL_PERMISO (id_rol, id_permiso) VALUES 
(3, 1), (3, 2), (3, 3);

-- ============================================
-- 12. ASIGNAR OPERADORES A DEPARTAMENTOS
-- ============================================
INSERT INTO MIEMBRO_DPTO (id_operador, id_depto, rol, fecha_asignacion) VALUES 
(1, 3, 'Jefe', NOW()),
(2, 1, 'Supervisor', NOW()),
(3, 1, 'Agente', NOW()),
(4, 2, 'Agente', NOW());

-- ============================================
-- 13. TICKETS DE PRUEBA (opcional)
-- ============================================
-- Ticket 1: Nuevo
INSERT INTO TICKET (titulo, tipo_ticket, descripcion, id_estado, id_prioridad, id_usuarioext, id_club, id_sla) 
VALUES ('Problema con acceso a la plataforma', 'Publico', 'No puedo acceder a mi cuenta desde ayer', 1, 2, 1, 1, 1);

-- Ticket 2: En proceso
INSERT INTO TICKET (titulo, tipo_ticket, descripcion, id_estado, id_prioridad, id_usuarioext, id_club, id_sla) 
VALUES ('Consulta sobre horarios', 'Publico', 'Quisiera saber los horarios de atención', 2, 4, 2, 2, 1);

-- Ticket 3: Resuelto
INSERT INTO TICKET (titulo, tipo_ticket, descripcion, id_estado, id_prioridad, id_usuarioext, id_club, id_sla, fecha_resolucion) 
VALUES ('Error en facturación', 'Publico', 'Me cobraron de más este mes', 3, 1, 3, 1, 2, NOW());

-- ============================================
-- 14. ASIGNAR OPERADORES A TICKETS
-- ============================================
INSERT INTO TICKET_OPERADOR (id_operador, id_ticket, rol, fecha_asignacion) VALUES 
(3, 1, 'Owner', NOW()),
(4, 2, 'Owner', NOW()),
(3, 3, 'Owner', DATE_SUB(NOW(), INTERVAL 1 DAY));

-- ============================================
-- 15. MENSAJES INICIALES DE LOS TICKETS
-- ============================================
INSERT INTO MENSAJE (tipo_mensaje, asunto, contenido, remitente_id, remitente_tipo, estado_mensaje, id_ticket, id_canal) VALUES 
('Publico', 'Problema con acceso a la plataforma', 'No puedo acceder a mi cuenta desde ayer. Me sale error de contraseña incorrecta pero estoy seguro que es la correcta.', 1, 'Usuario', 'Normal', 1, 1),
('Publico', 'Consulta sobre horarios', '¿Cuáles son los horarios de atención para el gimnasio?', 2, 'Usuario', 'Normal', 2, 2),
('Publico', 'Error en facturación', 'En mi última boleta aparece un cargo de $50.000 que no reconozco', 3, 'Usuario', 'Normal', 3, 1);

-- ============================================
-- 16. ETIQUETAS
-- ============================================
INSERT INTO ETIQUETA (nombre, color) VALUES 
('Urgente', '#FF0000'),
('Facturación', '#0000FF'),
('Técnico', '#00FF00'),
('Consulta', '#FFFF00'),
('Reclamo', '#FF6600');

-- ============================================
-- 17. ASIGNAR ETIQUETAS A TICKETS
-- ============================================
INSERT INTO TICKET_ETIQUETA (id_ticket, id_etiqueta) VALUES 
(1, 3),  -- Técnico
(2, 4),  -- Consulta
(3, 1),  -- Urgente
(3, 2);  -- Facturación

-- ============================================
-- 18. HISTORIAL DE ACCIONES
-- ============================================
INSERT INTO HISTORIAL_ACCIONES_TICKET (id_ticket, id_operador, accion, valor_anterior, valor_nuevo) VALUES 
(1, 3, 'Ticket creado', NULL, 'Estado: Nuevo'),
(1, 3, 'Operador asignado', NULL, 'Operador 3 como Owner'),
(2, 4, 'Ticket creado', NULL, 'Estado: Nuevo'),
(2, 4, 'Cambio de estado', 'Nuevo', 'En Proceso'),
(3, 3, 'Ticket creado', NULL, 'Estado: Nuevo'),
(3, 3, 'Cambio de estado', 'Nuevo', 'Resuelto');

-- ============================================
-- FIN DE DATOS INICIALES
-- ============================================

SELECT 'Datos iniciales insertados correctamente' as mensaje;
