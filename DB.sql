-- Create the database
CREATE DATABASE proctoring_app;

-- Use the database
USE proctoring_app;

-- 1. Students Table (with Warnings Included)
CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,  -- Unique student ID
    first_name VARCHAR(100),                    -- Student's first name
    last_name VARCHAR(100),                     -- Student's last name
    email VARCHAR(100) UNIQUE NOT NULL,         -- Student's email (unique)
    enrolled_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Date of enrollment
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',  -- Status of the student
    warning_counter INT DEFAULT 0,              -- Counter for the number of warnings
    last_warning_date TIMESTAMP,                -- Date when the last warning was issued
    warnings_details TEXT                       -- Optional: Details about the warnings (e.g., comma-separated reasons)
);

-- 2. Tests Table
CREATE TABLE tests (
    test_id INT AUTO_INCREMENT PRIMARY KEY,      -- Unique test ID
    test_name VARCHAR(255) NOT NULL,              -- Name of the test
    test_url VARCHAR(255) NOT NULL,               -- URL where the test is hosted
    test_status ENUM('pending', 'active', 'completed', 'expired') DEFAULT 'pending',  -- Test status
    start_time TIMESTAMP,                         -- Start time of the test
    end_time TIMESTAMP,                           -- End time of the test
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp when the test was created
);

-- 3. Detections Table (Tracks suspicious events)
CREATE TABLE detections (
    detection_id INT AUTO_INCREMENT PRIMARY KEY, -- Unique detection ID
    student_id INT,                             -- Student ID (foreign key)
    test_id INT,                                -- Test ID (foreign key)
    detection_type VARCHAR(100),                -- Type of detection (e.g., "face detection", "window switching")
    detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Time when detection occurred
    status ENUM('resolved', 'unresolved') DEFAULT 'unresolved',  -- Status of the detection
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (test_id) REFERENCES tests(test_id)
);

-- Sample Data Insertion (for testing purposes)

-- Insert students
INSERT INTO students (first_name, last_name, email, status) VALUES 
('John', 'Doe', 'john.doe@example.com', 'active'),
('Jane', 'Smith', 'jane.smith@example.com', 'inactive'),
('Mark', 'Johnson', 'mark.johnson@example.com', 'active');

-- Insert tests
INSERT INTO tests (test_name, test_url, test_status, start_time, end_time) VALUES 
('Math Test', 'http://example.com/math', 'active', '2025-02-20 10:00:00', '2025-02-20 12:00:00'),
('Science Test', 'http://example.com/science', 'pending', '2025-02-21 14:00:00', '2025-02-21 16:00:00');

-- Insert detections
INSERT INTO detections (student_id, test_id, detection_type, status) VALUES 
(1, 1, 'window switching', 'unresolved'),
(2, 1, 'face detection', 'resolved'),
(3, 2, 'suspicious movement', 'unresolved');

-- Example query to get all students with warning info
SELECT student_id, first_name, last_name, email, warning_counter, last_warning_date, warnings_details FROM students;

-- Example query to get all detections for a specific student (e.g., student_id = 1)
SELECT * FROM detections WHERE student_id = 1;

-- Example query to get all detections for a specific test (e.g., test_id = 1)
SELECT * FROM detections WHERE test_id = 1;