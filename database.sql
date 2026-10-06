-- Smart Parking System Database Schema
CREATE DATABASE IF NOT EXISTS smart_parking;

USE smart_parking;

-- Table for parking slot definitions and live status
CREATE TABLE IF NOT EXISTS parking_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_number VARCHAR(10) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'Available'
);

-- Table for tracking reservations & billing
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    vehicle_number VARCHAR(20) NOT NULL,
    slot_number VARCHAR(10) NOT NULL,
    entry_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    exit_time DATETIME NULL,
    amount DECIMAL(10,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Active'
);

-- Insert default slots if not already present
INSERT IGNORE INTO parking_slots (slot_number, status) VALUES
('A1', 'Available'),
('A2', 'Available'),
('A3', 'Available'),
('A4', 'Available'),
('B1', 'Available'),
('B2', 'Available'),
('B3', 'Available'),
('B4', 'Available');
