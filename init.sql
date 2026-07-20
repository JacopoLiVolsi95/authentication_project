-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password) VALUES
('test-user', '$2b$12$XCUiSGZxQMzoR5WLUoCvquO7sXXIZ7Vew1JrbiahCXS.rutKxjX9K');

-- Protected services table
CREATE TABLE protected_services (
    id SERIAL PRIMARY KEY,
    protected_service_id INT NOT NULL UNIQUE,
    protected_service_name VARCHAR(100) NOT NULL
);

-- Protected services token table
CREATE TABLE protected_services_tokens (
    id SERIAL PRIMARY KEY,
    protected_service_id INT REFERENCES protected_services(protected_service_id) ON DELETE CASCADE,
    username VARCHAR(100) REFERENCES users(username) ON DELETE CASCADE,
    temporary_token VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);