-- PostgreSQL Initialization Script for Company Leave Management System
-- This script sets up the database with proper permissions and optimizations

-- Create application user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'leave_user') THEN

      CREATE ROLE leave_user LOGIN PASSWORD 'secure_password_change_me';
   END IF;
END
$do$;

-- Create database if not exists
SELECT 'CREATE DATABASE leave_system OWNER leave_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'leave_system')\gexec

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE leave_system TO leave_user;

-- Connect to the application database
\c leave_system;

-- Set up database optimizations
ALTER DATABASE leave_system SET timezone TO 'UTC';
ALTER DATABASE leave_system SET default_text_search_config TO 'pg_catalog.english';

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set up proper permissions for the application user
GRANT ALL ON SCHEMA public TO leave_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO leave_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO leave_user;

-- Default permissions for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO leave_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO leave_user;

-- Performance optimizations
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Security settings
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Reload configuration
SELECT pg_reload_conf();