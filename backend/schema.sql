-- 1. Criação do banco
CREATE DATABASE IF NOT EXISTS ajudanoizapp_db;
USE ajudanoizapp_db;

-- 2. Clientes (Pai - Não depende de ninguém)
CREATE TABLE IF NOT EXISTS clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    whatsapp VARCHAR(20),
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo TINYINT(1) DEFAULT 1
);

-- 3. Usuários (Pai - Não depende de ninguém)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    cargo ENUM('admin', 'tecnico') DEFAULT 'tecnico',
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Chamados (Filha - Depende de Clientes e Usuários)
CREATE TABLE IF NOT EXISTS chamados(
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT,
    cliente_nome VARCHAR(100) NOT NULL,
    cliente_email VARCHAR(100) NOT NULL,
    cliente_whatsapp VARCHAR(15) NOT NULL,
    servico_titulo VARCHAR(150) NOT NULL,
    descricao TEXT NOT NULL,
    tecnico_id INT NULL,
    ativo TINYINT(1) DEFAULT 1,
    status ENUM('Novo', 'Em progresso', 'Agendado', 'Ag_pendente', 'Suspenso', 'Concluído', 'Cancelado') DEFAULT 'Novo',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_exclusao DATETIME NULL,
    FOREIGN KEY (tecnico_id) REFERENCES usuarios(id),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    deseja_agendar VARCHAR(3) DEFAULT 'NÃO',
    data_proposta DATETIME NULL
);

-- 5. Atividades e Histórico (Netas - Dependem de Chamados e Usuários)
CREATE TABLE IF NOT EXISTS atividades(
    id INT AUTO_INCREMENT PRIMARY KEY,
    chamado_id INT,
    descricao TEXT NOT NULL,
    data_atividade TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tempo_gasto INT NOT NULL,
    FOREIGN KEY (chamado_id) REFERENCES chamados(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS historico_chamados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chamado_id INT NOT NULL,
    usuario_id INT NOT NULL,
    acao TEXT NOT NULL,
    data_acao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chamado_id) REFERENCES chamados(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- 6. Cria a tabela de agendamentos confirmados
CREATE TABLE IF NOT EXISTS agendamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chamado_id INT NOT NULL,
    tecnico_id INT NOT NULL,
    data_hora DATETIME NOT NULL,
    status VARCHAR(20) DEFAULT 'Confirmado',
    FOREIGN KEY (chamado_id) REFERENCES chamados(id),
    FOREIGN KEY (tecnico_id) REFERENCES usuarios(id),
    -- Garante que um técnico não tenha dois agendamentos no mesmo horário
    UNIQUE KEY tecnico_horario (tecnico_id, data_hora) 
);