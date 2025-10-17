-- Initialize PostgreSQL database with proper user and permissions
-- This script runs during database initialization

-- Create the application user with proper permissions
DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'vf_app') THEN
      CREATE ROLE vf_app WITH LOGIN PASSWORD 'vf_app_secure_2025!';
   END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE voiceflow_prod TO vf_app;
GRANT ALL ON SCHEMA public TO vf_app;

-- Ensure the admin user has all privileges
GRANT ALL PRIVILEGES ON DATABASE voiceflow_prod TO vf_admin;
GRANT ALL ON SCHEMA public TO vf_admin;