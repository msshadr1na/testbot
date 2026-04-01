DROP TABLE IF EXISTS review CASCADE;
DROP TABLE IF EXISTS booking CASCADE;
DROP TABLE IF EXISTS training CASCADE;
DROP TABLE IF EXISTS gym CASCADE;
DROP TABLE IF EXISTS organization_member CASCADE;
DROP TABLE IF EXISTS organization CASCADE;
DROP TABLE IF EXISTS settings CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS training_type CASCADE;
DROP TABLE IF EXISTS role CASCADE;
DROP TABLE IF EXISTS invites CASCADE;

CREATE TABLE role (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO role (id, name) VALUES 
(1, 'owner'),
(2, 'trainer'),
(3, 'client');

CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    notification_settings JSONB NOT null
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    phone VARCHAR(20),
    first_name VARCHAR(50) NOT null,
    last_name VARCHAR(50) NOT null,
    middle_name VARCHAR(50),
    settings_id INT not null,
    foreign key (settings_id) references settings(id) on delete restrict
);


CREATE TABLE organization (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE gym (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL DEFAULT 'Зал',
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE
);

CREATE TABLE organization_member (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES role(id),
    UNIQUE (user_id, organization_id)
);

CREATE TABLE training_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE training (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    gym_id INTEGER NOT NULL REFERENCES gym(id) ON DELETE CASCADE,
    trainer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    date_start TIMESTAMP NOT NULL,
    date_end TIMESTAMP NOT NULL,
    type_id INTEGER NOT NULL REFERENCES training_type(id),
    max_clients INTEGER NOT NULL CHECK (max_clients > 0),
    CHECK (date_end > date_start)
);

CREATE TABLE booking (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    training_id INTEGER NOT NULL REFERENCES training(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, training_id)
);

CREATE TABLE review (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    training_id INTEGER NOT NULL REFERENCES training(id) ON DELETE CASCADE,
    grade INTEGER NOT NULL CHECK (grade BETWEEN 1 AND 5),
    text TEXT
);

CREATE TABLE invites (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES role(id),
    code VARCHAR(64) NOT NULL UNIQUE
);