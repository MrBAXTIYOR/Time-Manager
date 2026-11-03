-- Runs once, on first start of an empty MySQL volume.
-- The app user only owns the app database by default; give it the test DB too.
CREATE DATABASE IF NOT EXISTS tms_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON tms_test.* TO 'tms'@'%';
FLUSH PRIVILEGES;
