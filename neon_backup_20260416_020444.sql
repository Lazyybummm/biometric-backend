-- PostgreSQL database export
-- Generated at 20260416_020444


-- Table: commands
DROP TABLE IF EXISTS "commands" CASCADE;
CREATE TABLE "commands" (
  "id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "device_id" text NOT NULL,
  "command" text NOT NULL,
  "target_id" integer,
  "status" USER-DEFINED,
  "created_at" timestamp with time zone
);

COPY "commands" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
2,1,ESP32_MAIN_GATE,enroll,1,SUCCESS,2026-04-15 16:33:19.890656+00
3,1,ESP32_MAIN_GATE,delete,1,PENDING,2026-04-15 16:33:56.978052+00
4,1,ESP32_MAIN_GATE,enroll,1,SUCCESS,2026-04-15 16:34:09.929167+00
5,1,ESP32_MAIN_GATE,delete,1,PENDING,2026-04-15 20:06:28.058001+00
\.

-- Table: departments
DROP TABLE IF EXISTS "departments" CASCADE;
CREATE TABLE "departments" (
  "department_id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "department_name" text NOT NULL
);

COPY "departments" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
1,1,Office
\.

-- Table: employees
DROP TABLE IF EXISTS "employees" CASCADE;
CREATE TABLE "employees" (
  "employee_id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "name" text NOT NULL,
  "department_id" integer,
  "finger_id" integer,
  "is_active" boolean
);

COPY "employees" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
\.

-- Table: users
DROP TABLE IF EXISTS "users" CASCADE;
CREATE TABLE "users" (
  "id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "finger_id" integer NOT NULL,
  "name" text NOT NULL
);

COPY "users" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
2,1,1,Aakash
3,2,1,Aakash TBI
\.

-- Table: tenants
DROP TABLE IF EXISTS "tenants" CASCADE;
CREATE TABLE "tenants" (
  "id" integer NOT NULL,
  "name" text NOT NULL,
  "api_key" text NOT NULL,
  "created_at" timestamp with time zone
);

COPY "tenants" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
1,TBI-GEU,tbi_geu_key_001,2026-04-15 15:23:12.288272+00
2,Test Company,test_api_key,2026-04-15 20:11:48.048312+00
3,My New Tenenet,032559a65ac8de14ddafa9311987100d,2026-04-15 20:25:39.591774+00
\.

-- Table: admin_users
DROP TABLE IF EXISTS "admin_users" CASCADE;
CREATE TABLE "admin_users" (
  "id" integer NOT NULL,
  "username" text NOT NULL,
  "password" text NOT NULL,
  "api_token" text,
  "role" USER-DEFINED NOT NULL,
  "tenant_id" integer
);

COPY "admin_users" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
1,admin,$2b$12$MTc50aywfVUjVWKWFv/Vg.v.kKrUh.lfjqmjPhO58mU3Rurx/VZ7G,676beafe94f76894e22efe7569c6a1f1be6dacdc25e688b10b93ac1c241b8b34,super_admin,NULL
2,TBI-GEU,$2b$12$TlTPqTyEJbarMwom5tv0b.06XckRad685l3aFa7DI8yk6n/LKf4G.,b6c66afe5d3bdfa89f3f11487d10ccb8bf737ebfb52da70ae4effeb88f5b36d5,super_admin,NULL
\.

-- Table: devices
DROP TABLE IF EXISTS "devices" CASCADE;
CREATE TABLE "devices" (
  "id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "device_id" text NOT NULL,
  "secret_key" text NOT NULL,
  "status" text,
  "last_seen" timestamp with time zone
);

COPY "devices" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
3,2,ESP32_MAIN_GATE2,secret123,NULL,NULL
1,1,ESP32_MAIN_GATE,secret123,online,2026-04-15 14:44:29.610878+00
\.

-- Table: attendance_logs
DROP TABLE IF EXISTS "attendance_logs" CASCADE;
CREATE TABLE "attendance_logs" (
  "id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "device_id" text NOT NULL,
  "finger_id" integer NOT NULL,
  "timestamp" timestamp with time zone,
  "record_type" text NOT NULL
);

COPY "attendance_logs" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
1,1,ESP32_MAIN_GATE,1,2026-04-15 16:34:29.645975+00,IN
\.

-- Table: leaves
DROP TABLE IF EXISTS "leaves" CASCADE;
CREATE TABLE "leaves" (
  "leave_id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "employee_id" integer,
  "leave_type" text,
  "start_date" date,
  "end_date" date,
  "reason" text,
  "status" text,
  "created_at" timestamp with time zone
);

COPY "leaves" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
\.

-- Table: holidays
DROP TABLE IF EXISTS "holidays" CASCADE;
CREATE TABLE "holidays" (
  "holiday_id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "name" text NOT NULL,
  "holiday_date" date NOT NULL
);

COPY "holidays" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
\.

-- Table: notifications
DROP TABLE IF EXISTS "notifications" CASCADE;
CREATE TABLE "notifications" (
  "notification_id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "user_id" integer,
  "message" text,
  "is_read" boolean,
  "created_at" timestamp with time zone
);

COPY "notifications" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
\.

-- Table: settings
DROP TABLE IF EXISTS "settings" CASCADE;
CREATE TABLE "settings" (
  "id" integer NOT NULL,
  "tenant_id" integer NOT NULL,
  "office_start_time" text,
  "office_end_time" text,
  "late_threshold_minutes" integer
);

COPY "settings" FROM STDIN WITH (FORMAT csv, NULL 'NULL');
1,1,09:00,17:00,15
\.
