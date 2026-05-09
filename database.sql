CREATE DATABASE student_performance_db;
USE student_performance_db;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE predictions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ag_number VARCHAR(20) NOT NULL,
  student_name VARCHAR(100) NOT NULL,
  mid_marks FLOAT NOT NULL,
  assignment_marks FLOAT NOT NULL,
  final_marks FLOAT NOT NULL,
  total_marks FLOAT NOT NULL,
  obtained_marks FLOAT NOT NULL,
  percentage FLOAT NOT NULL,
  grade VARCHAR(2) NOT NULL,
  status VARCHAR(20) NOT NULL,
  predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);