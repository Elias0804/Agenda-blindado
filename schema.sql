-- =====================================
-- SCRIPT COMPLETO DO BANCO DE DADOS
-- agenda.db
-- =====================================

-- ========================
-- CLIENTES
-- ========================
DROP TABLE IF EXISTS clients;
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================
-- PROFISSIONAIS
-- ========================
DROP TABLE IF EXISTS professionals;
CREATE TABLE professionals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialty TEXT,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================
-- SERVIÇOS
-- ========================
DROP TABLE IF EXISTS services;
CREATE TABLE services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    duration INTEGER NOT NULL,       -- em minutos
    price REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================
-- AGENDAMENTOS
-- ========================
DROP TABLE IF EXISTS schedules;
CREATE TABLE schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    professional_id INTEGER,
    service_id INTEGER,
    date_time TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(professional_id) REFERENCES professionals(id),
    FOREIGN KEY(service_id) REFERENCES services(id)
);

-- ========================
-- ESTOQUE
-- ========================
DROP TABLE IF EXISTS inventory;
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT CHECK(category IN ('uso', 'venda')) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    usage_per_service REAL DEFAULT 0,   -- apenas p/ produtos de uso
    unit_price REAL DEFAULT 0.0,        -- apenas p/ produtos de venda
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================
-- PRODUTOS UTILIZADOS EM SERVIÇOS
-- ========================
DROP TABLE IF EXISTS service_products;
CREATE TABLE service_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity_used REAL NOT NULL DEFAULT 1,
    FOREIGN KEY(service_id) REFERENCES services(id),
    FOREIGN KEY(product_id) REFERENCES inventory(id)
);

-- ========================
-- CONSULTA AUXILIAR: TOTAL USADO POR PRODUTO
-- ========================
-- Exemplo de uso: total consumido de cada produto em serviços realizados
-- (substitui o campo calculado "total_used" do seu template)
-- Rode esta query no SQLite:
-- SELECT p.name, sp.product_id, SUM(sp.quantity_used) AS total_used
-- FROM service_products sp
-- JOIN inventory p ON p.id = sp.product_id
-- GROUP BY sp.product_id;
