-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema sistema_ticket_recrear
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema sistema_ticket_recrear
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `sistema_ticket_recrear` DEFAULT CHARACTER SET utf8mb4 ;
USE `sistema_ticket_recrear` ;

-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`USUARIO_EXT`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`USUARIO_EXT` (
  `id_usuario` INT NOT NULL AUTO_INCREMENT,
  `rut` VARCHAR(12) CHARACTER SET 'utf8mb4' NULL DEFAULT NULL,
  `nombre` VARCHAR(45) CHARACTER SET 'utf8mb4' NULL DEFAULT NULL,
  `telefono` VARCHAR(15) CHARACTER SET 'utf8mb4' NULL DEFAULT NULL,
  `email` VARCHAR(100) CHARACTER SET 'utf8mb4' NOT NULL,
  `fecha_creacion` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `id_gestion` INT NULL DEFAULT NULL,
  `id_web` INT NULL DEFAULT NULL,
  `existe_flex` TINYINT NOT NULL,
  `deleted_at` DATETIME NULL DEFAULT NULL,
  `deleted_by` INT NULL DEFAULT NULL,
  PRIMARY KEY (`id_usuario`),
  UNIQUE INDEX `email_UNIQUE` (`email` ASC) VISIBLE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`ESTADO`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`ESTADO` (
  `id_estado` INT NOT NULL AUTO_INCREMENT,
  `descripcion` VARCHAR(20) CHARACTER SET 'utf8mb4' NOT NULL,
  PRIMARY KEY (`id_estado`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`CLUB`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`CLUB` (
  `id_club` INT NOT NULL AUTO_INCREMENT,
  `nom_club` VARCHAR(45) CHARACTER SET 'utf8mb4' NOT NULL,
  PRIMARY KEY (`id_club`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`PRIORIDAD`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`PRIORIDAD` (
  `id_prioridad` INT NOT NULL AUTO_INCREMENT,
  `jerarquia` INT NOT NULL DEFAULT 0,
  `descripcion` VARCHAR(20) CHARACTER SET 'utf8mb4' NOT NULL,
  PRIMARY KEY (`id_prioridad`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`SLA`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`SLA` (
  `id_sla` INT NOT NULL AUTO_INCREMENT,
  `nombre` VARCHAR(50) NOT NULL,
  `tiempo_primera_respuesta_min` INT NOT NULL,
  `tiempo_resolucion_min` INT NOT NULL,
  `activo` TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id_sla`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`TICKET`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`TICKET` (
  `id_ticket` INT NOT NULL AUTO_INCREMENT,
  `titulo` TEXT NOT NULL,
  `tipo_ticket` ENUM('Privado', 'Publico') NOT NULL,
  `descripcion` TEXT NULL DEFAULT NULL,
  `fecha_ini` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` DATETIME NULL DEFAULT NULL,
  `deleted_by` INT NULL DEFAULT NULL,
  `fecha_primera_respuesta` DATETIME NULL,
  `fecha_resolucion` DATETIME NULL,
  `id_estado` INT NOT NULL,
  `id_prioridad` INT NOT NULL,
  `id_usuarioext` INT NULL,
  `id_club` INT NOT NULL,
  `id_sla` INT NOT NULL,
  PRIMARY KEY (`id_ticket`),
  INDEX `fk_TICKET_USUARIO_idx` (`id_usuarioext` ASC) VISIBLE,
  INDEX `fk_TICKET_ESTADOS1_idx` (`id_estado` ASC) VISIBLE,
  INDEX `fk_TICKET_CLUB1_idx` (`id_club` ASC) VISIBLE,
  INDEX `fk_TICKET_PRIORIDAD1_idx` (`id_prioridad` ASC) VISIBLE,
  INDEX `fk_TICKET_SLA1_idx` (`id_sla` ASC) VISIBLE,
  CONSTRAINT `fk_TICKET_USUARIO`
    FOREIGN KEY (`id_usuarioext`)
    REFERENCES `sistema_ticket_recrear`.`USUARIO_EXT` (`id_usuario`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_TICKET_ESTADOS1`
    FOREIGN KEY (`id_estado`)
    REFERENCES `sistema_ticket_recrear`.`ESTADO` (`id_estado`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_TICKET_CLUB1`
    FOREIGN KEY (`id_club`)
    REFERENCES `sistema_ticket_recrear`.`CLUB` (`id_club`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_TICKET_PRIORIDAD1`
    FOREIGN KEY (`id_prioridad`)
    REFERENCES `sistema_ticket_recrear`.`PRIORIDAD` (`id_prioridad`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_TICKET_SLA1`
    FOREIGN KEY (`id_sla`)
    REFERENCES `sistema_ticket_recrear`.`SLA` (`id_sla`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`ROL_GLOBAL`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`ROL_GLOBAL` (
  `id_rol` INT NOT NULL AUTO_INCREMENT,
  `nombre` VARCHAR(50) NOT NULL,
  `activo` TINYINT NOT NULL DEFAULT 1,
  PRIMARY KEY (`id_rol`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`OPERADOR`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`OPERADOR` (
  `id_operador` INT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(512) CHARACTER SET 'utf8mb4' NOT NULL,
  `nombre` VARCHAR(256) CHARACTER SET 'utf8mb4' NOT NULL,
  `telefono` VARCHAR(20) CHARACTER SET 'utf8mb4' NULL DEFAULT NULL,
  `estado` TINYINT NOT NULL DEFAULT 0,
  `deleted_at` DATETIME NULL DEFAULT NULL,
  `deleted_by` INT NULL DEFAULT NULL,
  `id_rol_global` INT NOT NULL,
  PRIMARY KEY (`id_operador`),
  UNIQUE INDEX `email_UNIQUE` (`email` ASC) VISIBLE,
  INDEX `fk_OPERADOR_ROL1_idx` (`id_rol_global` ASC) VISIBLE,
  CONSTRAINT `fk_OPERADOR_ROL1`
    FOREIGN KEY (`id_rol_global`)
    REFERENCES `sistema_ticket_recrear`.`ROL_GLOBAL` (`id_rol`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;




-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`CANAL`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`CANAL` (
  `id_canal` INT NOT NULL,
  `nombre` VARCHAR(45) CHARACTER SET 'utf8mb4' NOT NULL,
  PRIMARY KEY (`id_canal`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`MENSAJE`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`MENSAJE` (
  `id_msg` INT NOT NULL AUTO_INCREMENT,
  `tipo_mensaje` ENUM('Privado', 'Publico') NOT NULL DEFAULT 'Publico',
  `asunto` VARCHAR(50) NOT NULL,
  `contenido` VARCHAR(500) CHARACTER SET 'utf8mb4' NULL DEFAULT NULL,
  `remitente_id` INT NOT NULL,
  `remitente_tipo` ENUM('Usuario', 'Operador') CHARACTER SET 'utf8mb4' NOT NULL,
  `estado_mensaje` ENUM('Normal', 'Editado', 'Eliminado') NOT NULL,
  `fecha_envio` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_edicion` DATETIME NULL DEFAULT NULL,
  `id_ticket` INT NOT NULL,
  `id_canal` INT NOT NULL,
  `deleted_at` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id_msg`),
  INDEX `fk_MENSAJE_TICKET1_idx` (`id_ticket` ASC) VISIBLE,
  INDEX `fk_MENSAJE_CANAL1_idx` (`id_canal` ASC) VISIBLE,
  CONSTRAINT `fk_MENSAJE_TICKET1`
    FOREIGN KEY (`id_ticket`)
    REFERENCES `sistema_ticket_recrear`.`TICKET` (`id_ticket`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_MENSAJE_CANAL1`
    FOREIGN KEY (`id_canal`)
    REFERENCES `sistema_ticket_recrear`.`CANAL` (`id_canal`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`ADJUNTO`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`ADJUNTO` (
  `id_adj` INT NOT NULL AUTO_INCREMENT,
  `nom_adj` VARCHAR(100) NOT NULL,
  `ruta` VARCHAR(500) NULL DEFAULT NULL,
  `id_msg` INT NOT NULL,
  `deleted_at` DATETIME NULL DEFAULT NULL,
  `deleted_by` INT NULL DEFAULT NULL,
  PRIMARY KEY (`id_adj`),
  INDEX `fk_ADJUNTO_MENSAJE1_idx` (`id_msg` ASC) VISIBLE,
  CONSTRAINT `fk_ADJUNTO_MENSAJE1`
    FOREIGN KEY (`id_msg`)
    REFERENCES `sistema_ticket_recrear`.`MENSAJE` (`id_msg`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`TICKET_OPERADOR`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`TICKET_OPERADOR` (
  `id_operador` INT NOT NULL,
  `id_ticket` INT NOT NULL,
  `rol` ENUM('Owner', 'Colaborador', 'Agente') NOT NULL,
  `fecha_asignacion` DATETIME NOT NULL,
  `fecha_desasignacion` DATETIME NULL,
  PRIMARY KEY (`id_operador`, `id_ticket`),
  INDEX `fk_OPERADOR_has_TICKET_TICKET2_idx` (`id_ticket` ASC) VISIBLE,
  INDEX `fk_OPERADOR_has_TICKET_OPERADOR2_idx` (`id_operador` ASC) VISIBLE,
  CONSTRAINT `fk_OPERADOR_has_TICKET_OPERADOR2`
    FOREIGN KEY (`id_operador`)
    REFERENCES `sistema_ticket_recrear`.`OPERADOR` (`id_operador`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_OPERADOR_has_TICKET_TICKET2`
    FOREIGN KEY (`id_ticket`)
    REFERENCES `sistema_ticket_recrear`.`TICKET` (`id_ticket`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`DEPARTAMENTO`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`DEPARTAMENTO` (
  `id_depto` INT NOT NULL AUTO_INCREMENT,
  `descripcion` VARCHAR(45) NOT NULL,
  `email` VARCHAR(300) NOT NULL,
  `operador_default` INT NOT NULL,
  `recibe_externo` TINYINT NOT NULL,
  PRIMARY KEY (`id_depto`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`VISUALIZACION_DP`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`VISUALIZACION_DP` (
  `id_depto` INT NOT NULL,
  `id_operador` INT NOT NULL,
  PRIMARY KEY (`id_depto`, `id_operador`),
  INDEX `fk_DEPARTAMENTO_has_OPERADOR_OPERADOR1_idx` (`id_operador` ASC) VISIBLE,
  INDEX `fk_DEPARTAMENTO_has_OPERADOR_DEPARTAMENTO1_idx` (`id_depto` ASC) VISIBLE,
  CONSTRAINT `fk_DEPARTAMENTO_has_OPERADOR_DEPARTAMENTO1`
    FOREIGN KEY (`id_depto`)
    REFERENCES `sistema_ticket_recrear`.`DEPARTAMENTO` (`id_depto`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_DEPARTAMENTO_has_OPERADOR_OPERADOR1`
    FOREIGN KEY (`id_operador`)
    REFERENCES `sistema_ticket_recrear`.`OPERADOR` (`id_operador`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`MIEMBRO_DPTO`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`MIEMBRO_DPTO` (
  `id_operador` INT NOT NULL,
  `id_depto` INT NOT NULL,
  `rol` ENUM('Agente', 'Supervisor', 'Jefe') NOT NULL,
  `fecha_asignacion` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_desasignacion` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id_operador`, `id_depto`),
  INDEX `fk_OPERADOR_has_DEPARTAMENTO_DEPARTAMENTO1_idx` (`id_depto` ASC) VISIBLE,
  INDEX `fk_OPERADOR_has_DEPARTAMENTO_OPERADOR1_idx` (`id_operador` ASC) VISIBLE,
  CONSTRAINT `fk_OPERADOR_has_DEPARTAMENTO_OPERADOR1`
    FOREIGN KEY (`id_operador`)
    REFERENCES `sistema_ticket_recrear`.`OPERADOR` (`id_operador`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_OPERADOR_has_DEPARTAMENTO_DEPARTAMENTO1`
    FOREIGN KEY (`id_depto`)
    REFERENCES `sistema_ticket_recrear`.`DEPARTAMENTO` (`id_depto`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`HISTORIAL_ACCIONES_TICKET`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`HISTORIAL_ACCIONES_TICKET` (
  `id_historial_ticket` INT NOT NULL AUTO_INCREMENT,
  `id_ticket` INT NOT NULL,
  `id_operador` INT NULL,
  `id_usuarioext` INT NULL,
  `accion` VARCHAR(100) NOT NULL,
  `valor_anterior` VARCHAR(100) NULL DEFAULT NULL,
  `valor_nuevo` VARCHAR(100) NULL DEFAULT NULL,
  `fecha` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_historial_ticket`),
  INDEX `fk_HISTORIAL_TICKET_TICKET1_idx` (`id_ticket` ASC) VISIBLE,
  INDEX `fk_HISTORIAL_TICKET_OPERADOR1_idx` (`id_operador` ASC) VISIBLE,
  INDEX `fk_HISTORIAL_ACCIONES_TICKET_USUARIO_EXT1_idx` (`id_usuarioext` ASC) VISIBLE,
  CONSTRAINT `fk_HISTORIAL_TICKET_TICKET1`
    FOREIGN KEY (`id_ticket`)
    REFERENCES `sistema_ticket_recrear`.`TICKET` (`id_ticket`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_HISTORIAL_TICKET_OPERADOR1`
    FOREIGN KEY (`id_operador`)
    REFERENCES `sistema_ticket_recrear`.`OPERADOR` (`id_operador`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_HISTORIAL_ACCIONES_TICKET_USUARIO_EXT1`
    FOREIGN KEY (`id_usuarioext`)
    REFERENCES `sistema_ticket_recrear`.`USUARIO_EXT` (`id_usuario`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`RESPUESTA_RAPIDA`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`RESPUESTA_RAPIDA` (
  `id_respuesta` INT NOT NULL AUTO_INCREMENT,
  `respuesta_operador` INT NOT NULL,
  `titulo` VARCHAR(100) NOT NULL,
  `contenido` TEXT NOT NULL,
  `categoria` VARCHAR(45) NOT NULL,
  `visibilidad` ENUM('Privado', 'Publico') NOT NULL DEFAULT 'Privado',
  `veces_usada` INT NOT NULL DEFAULT 0,
  `activa` TINYINT NULL,
  `deleted_at` DATETIME NULL DEFAULT NULL,
  `deleted_by` INT NULL DEFAULT NULL,
  PRIMARY KEY (`id_respuesta`),
  INDEX `fk_RESPUESTA_RAPIDA_OPERADOR1_idx` (`respuesta_operador` ASC) VISIBLE,
  CONSTRAINT `fk_RESPUESTA_RAPIDA_OPERADOR1`
    FOREIGN KEY (`respuesta_operador`)
    REFERENCES `sistema_ticket_recrear`.`OPERADOR` (`id_operador`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`ETIQUETA`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`ETIQUETA` (
  `id_etiqueta` INT NOT NULL AUTO_INCREMENT,
  `nombre` VARCHAR(50) NOT NULL,
  `color` VARCHAR(7) NULL,
  PRIMARY KEY (`id_etiqueta`),
  UNIQUE INDEX `nombre_UNIQUE` (`nombre` ASC) VISIBLE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`TICKET_ETIQUETA`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`TICKET_ETIQUETA` (
  `id_ticket` INT NOT NULL,
  `id_etiqueta` INT NOT NULL,
  PRIMARY KEY (`id_ticket`, `id_etiqueta`),
  INDEX `fk_TICKET_has_ETIQUETA_ETIQUETA1_idx` (`id_etiqueta` ASC) VISIBLE,
  INDEX `fk_TICKET_has_ETIQUETA_TICKET1_idx` (`id_ticket` ASC) VISIBLE,
  CONSTRAINT `fk_TICKET_has_ETIQUETA_TICKET1`
    FOREIGN KEY (`id_ticket`)
    REFERENCES `sistema_ticket_recrear`.`TICKET` (`id_ticket`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_TICKET_has_ETIQUETA_ETIQUETA1`
    FOREIGN KEY (`id_etiqueta`)
    REFERENCES `sistema_ticket_recrear`.`ETIQUETA` (`id_etiqueta`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`PERMISO`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`PERMISO` (
  `id_permiso` INT NOT NULL AUTO_INCREMENT,
  `codigo` VARCHAR(50) NOT NULL,
  `descripcion` VARCHAR(45) NULL DEFAULT NULL,
  `activo` TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id_permiso`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `sistema_ticket_recrear`.`ROL_PERMISO`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sistema_ticket_recrear`.`ROL_PERMISO` (
  `id_rol` INT NOT NULL,
  `id_permiso` INT NOT NULL,
  PRIMARY KEY (`id_rol`, `id_permiso`),
  INDEX `fk_ROL_has_PERMISO_PERMISO1_idx` (`id_permiso` ASC) VISIBLE,
  INDEX `fk_ROL_has_PERMISO_ROL1_idx` (`id_rol` ASC) VISIBLE,
  CONSTRAINT `fk_ROL_has_PERMISO_ROL1`
    FOREIGN KEY (`id_rol`)
    REFERENCES `sistema_ticket_recrear`.`ROL_GLOBAL` (`id_rol`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_ROL_has_PERMISO_PERMISO1`
    FOREIGN KEY (`id_permiso`)
    REFERENCES `sistema_ticket_recrear`.`PERMISO` (`id_permiso`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
