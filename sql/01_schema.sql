-- Usar la base de datos creada
USE pt_db;

-- Tabla companies
CREATE TABLE IF NOT EXISTS companies (
    company_id VARCHAR(40) PRIMARY KEY,
    company_name VARCHAR(130) NOT NULL
);

-- Tabla charges
CREATE TABLE IF NOT EXISTS charges (
    id VARCHAR(40) PRIMARY KEY,
    company_id VARCHAR(40) NOT NULL,
    amount DECIMAL(16,2) NOT NULL,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);
