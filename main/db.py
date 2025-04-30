# main/db.py

import mysql.connector

def get_db():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='network_monitor'
    )
    return conn

def init_db():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password=''
    )
    cursor = conn.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS network_monitor")
    conn.database = 'network_monitor'

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user', -- 'admin' or 'user'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
