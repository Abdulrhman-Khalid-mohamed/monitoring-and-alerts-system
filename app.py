"""
System Monitor & Alerts - Main Application
A comprehensive monitoring system for websites, APIs, and system resources
"""

from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Import routes
from routes.monitor_routes import monitor_bp
from routes.metric_routes import metric_bp
from routes.alert_routes import alert_bp
from routes.analytics_routes import analytics_bp

# Import services
from services.monitor_service import MonitorService
from services.system_service import SystemService
from utils.database import init_db, get_db_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'monitor.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Register blueprints
app.register_blueprint(monitor_bp, url_prefix='/api/monitors')
app.register_blueprint(metric_bp, url_prefix='/api/metrics')
app.register_blueprint(alert_bp, url_prefix='/api/alerts')
app.register_blueprint(analytics_bp, url_prefix='/api/analytics')

# Initialize services
monitor_service = MonitorService()
system_service = SystemService()

# Initialize scheduler
scheduler = BackgroundScheduler()


def run_monitors():
    """Execute all active monitors"""
    try:
        logger.info("Running scheduled monitor checks...")
        monitor_service.check_all_monitors()
    except Exception as e:
        logger.error(f"Error running monitors: {str(e)}")


def run_system_monitor():
    """Execute system resource monitoring"""
    try:
        if os.getenv('SYSTEM_MONITOR_ENABLED', 'True').lower() == 'true':
            logger.info("Running system resource check...")
            system_service.collect_system_metrics()
    except Exception as e:
        logger.error(f"Error running system monitor: {str(e)}")


def cleanup_old_metrics():
    """Clean up old metrics data"""
    try:
        max_age_days = int(os.getenv('MAX_METRICS_AGE_DAYS', '30'))
        logger.info(f"Cleaning up metrics older than {max_age_days} days...")
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM metrics 
            WHERE timestamp < NOW() - INTERVAL '%s days'
        """, (max_age_days,))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Deleted {deleted} old metric records")
    except Exception as e:
        logger.error(f"Error cleaning up metrics: {str(e)}")


# Root endpoint
@app.route('/')
def index():
    """Root endpoint with API information"""
    return jsonify({
        'name': 'System Monitor & Alerts API',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'endpoints': {
            'monitors': '/api/monitors',
            'metrics': '/api/metrics',
            'alerts': '/api/alerts',
            'analytics': '/api/analytics',
            'system': '/api/system/metrics'
        },
        'documentation': 'https://github.com/yourusername/system-monitor'
    })


@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@app.route('/api/system/metrics')
def get_system_metrics():
    """Get current system metrics"""
    try:
        metrics = system_service.get_current_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


def start_scheduler():
    """Start the background scheduler"""
    check_interval = int(os.getenv('DEFAULT_CHECK_INTERVAL', '60'))
    system_interval = int(os.getenv('SYSTEM_CHECK_INTERVAL', '30'))
    
    # Schedule monitor checks
    scheduler.add_job(
        func=run_monitors,
        trigger="interval",
        seconds=check_interval,
        id='monitor_checks',
        name='Run monitor checks',
        replace_existing=True
    )
    
    # Schedule system monitoring
    scheduler.add_job(
        func=run_system_monitor,
        trigger="interval",
        seconds=system_interval,
        id='system_monitoring',
        name='Collect system metrics',
        replace_existing=True
    )
    
    # Schedule daily cleanup at 2 AM
    scheduler.add_job(
        func=cleanup_old_metrics,
        trigger="cron",
        hour=2,
        minute=0,
        id='cleanup_metrics',
        name='Clean up old metrics',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started successfully")


if __name__ == '__main__':
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Start scheduler
        logger.info("Starting background scheduler...")
        start_scheduler()
        
        # Run Flask app
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
        
        logger.info(f"Starting Flask application on {host}:{port}")
        app.run(host=host, port=port, debug=debug)
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
