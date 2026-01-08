-- Migración: convertir ROL_GLOBAL.nombre de ENUM a VARCHAR para permitir roles dinámicos
-- Fecha: 2026-01-08
-- Base: sistema_ticket_recrear
--
-- Importante:
-- - Este cambio permite nombres arbitrarios de rol (ya no limitados a 'Admin','Supervisor','Agente').
-- - No borra datos; solo cambia el tipo de la columna.
--
-- Recomendación: ejecutar con un usuario con permisos ALTER.

USE `sistema_ticket_recrear`;

-- Verificación opcional (antes):
-- SHOW COLUMNS FROM rol_global LIKE 'nombre';

ALTER TABLE rol_global
  MODIFY COLUMN nombre VARCHAR(50) NOT NULL;

-- Verificación opcional (después):
-- SHOW COLUMNS FROM rol_global LIKE 'nombre';

-- Nota opcional:
-- Si quieres evitar roles duplicados por nombre, puedes crear un índice único.
-- Ojo: fallará si ya existen duplicados.
-- ALTER TABLE rol_global ADD UNIQUE INDEX uq_rol_global_nombre (nombre);
