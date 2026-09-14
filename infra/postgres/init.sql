-- ---------------------------------------------------------------------------
-- PayrollFuturistic — Postgres init
-- Runs once when the Postgres container first creates its data volume.
-- ---------------------------------------------------------------------------

-- UUID generation (SQLAlchemy models use uuid, PKs)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Case-insensitive text (emails, tax codes)
CREATE EXTENSION IF NOT EXISTS "citext";

-- Schema segregation: payroll domain vs audit vs reference data
CREATE SCHEMA IF NOT EXISTS payroll;  
CREATE SCHEMA IF NOT EXISTS audit;  
CREATE SCHEMA IF NOT EXISTS reference;   

-- Default search_path for the application user
ALTER DATABASE payroll SET search_path TO payroll, reference, public;
  
