-- Criação do banco de dados
CREATE DATABASE IF NOT EXISTS ajudanoizapp_db;
USE ajudanoizapp_db;

-- Criação da tabela de Chamdos/Leads
CREATE TABLE IF NOT EXISTS chamados(
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_nome VARCHAR(100) NOT NULL,
    cliente_email VARCHAR(100) NOT NULL,
    cliente_whatsapp VARCHAR(15) NOT NULL,
    servico_titulo VARCHAR(150) NOT NULL,
    descricao TEXT NOT NULL,
    tecnico_id INT NULL,
    FOREIGN KEY (tecnico_id) REFERENCES usuarios(id),
    status ENUM('Novo', 'Em progresso', 'Suspenso', 'Concluído', 'Cancelado') DEFAULT 'Novo',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criação da tabela de atividades relacionadas aos chamados
CREATE TABLE IF NOT EXISTS atividades(
    id INT AUTO_INCREMENT PRIMARY KEY,
    chamado_id INT,
    descricao TEXT NOT NULL,
    data_atividade TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tempo_gasto INT NOT NULL,
    arquivo_caminho VARCHAR(255),
    FOREIGN KEY (chamado_id) REFERENCES chamados(id) ON DELETE CASCADE
);

-- Criação da tabela de usuários do sistema
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    cargo ENUM('admin', 'tecnico') DEFAULT 'tecnico',
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);