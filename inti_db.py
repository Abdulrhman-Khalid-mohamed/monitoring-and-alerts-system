"""
Database Initialization Script
Creates all necessary tables for the monitoring system
"""

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def create_tables():
    """Create all database tables"""
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Create monitors table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monitors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            url VARCHAR(512) NOT NULL,
            monitor_type VARCHAR(50) DEFAULT 'http',
            check_interval INTEGER DEFAULT 60,
            timeout INTEGER DEFAULT 10,
            alert_threshold INTEGER DEFAULT 3,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create metrics table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id SERIAL PRIMARY KEY,
            monitor_id INTEGER REFERENCES monitors(id) ON DELETE CASCADE,
            status_code INTEGER,
            response_time FLOAT,
            is_up BOOLEAN,
            error_message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create alerts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            monitor_id INTEGER REFERENCES monitors(id) ON DELETE CASCADE,
            alert_type VARCHAR(50),
            message TEXT,
            status VARCHAR(20) DEFAULT 'active',
            acknowledged BOOLEAN DEFAULT FALSE,
            acknowledged_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)
    
    # Create system_metrics table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id SERIAL PRIMARY KEY,
            cpu_percent FLOAT,
            memory_percent FLOAT,
            memory_used_gb FLOAT,
            memory_total_gb FLOAT,
            disk_percent FLOAT,
            disk_used_gb FLOAT,
            disk_total_gb FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_monitor_id 
        ON metrics(monitor_id)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
        ON metrics(timestamp)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_monitor_id 
        ON alerts(monitor_id)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_status 
        ON alerts(status)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp 
        ON system_metrics(timestamp)
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("✓ Database tables created successfully")


def seed_sample_data():
    """Add sample monitor data"""
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Check if monitors already exist
    cur.execute("SELECT COUNT(*) FROM monitors")
    count = cur.fetchone()[0]
    
    if count == 0:
        sample_monitors = [
            ('Google', 'https://www.google.com', 'http', 60, 10, 3),
            ('GitHub', 'https://github.com', 'http', 120, 15, 3),
            ('Example API', 'https://api.github.com', 'http', 60, 10, 3)
        ]
        
        for monitor in sample_monitors:
            cur.execute("""
                INSERT INTO monitors (name, url, monitor_type, check_interval, timeout, alert_threshold)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, monitor)
        
        conn.commit()
        print(f"✓ Added {len(sample_monitors)} sample monitors")
    else:
        print(f"✓ Database already contains {count} monitors")
    
    cur.close()
    conn.close()


if __name__ == '__main__':
    try:
        print("Initializing database...")
        create_tables()
        
        # Optional: Add sample data
        response = input("\nAdd sample monitors? (y/n): ")
        if response.lower() == 'y':
            seed_sample_data()
        
        print("\n✓ Database initialization complete!")
        
    except Exception as e:
        print(f"✗ Error initializing database: {str(e)}")
        raise
