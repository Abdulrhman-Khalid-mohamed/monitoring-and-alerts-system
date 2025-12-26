"""
Database Utilities
Handles database connections and common operations
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get a new database connection"""
    try:
        conn = psycopg2.connect(
            os.getenv('DATABASE_URL'),
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise


def init_db():
    """Initialize database tables if they don't exist"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
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
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()


def execute_query(query, params=None, fetch=True):
    """Execute a database query with error handling"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        
        if fetch:
            result = cur.fetchall()
            return result
        else:
            conn.commit()
            return cur.rowcount
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Query execution error: {str(e)}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def execute_many(query, params_list):
    """Execute multiple queries in batch"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.executemany(query, params_list)
        conn.commit()
        return cur.rowcount
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Batch execution error: {str(e)}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
