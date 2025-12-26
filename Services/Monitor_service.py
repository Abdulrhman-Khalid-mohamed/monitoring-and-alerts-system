"""
Monitor Service
Handles website/API monitoring and health checks
"""

import requests
import time
import logging
from datetime import datetime
from utils.database import get_db_connection
from services.alert_service import AlertService

logger = logging.getLogger(__name__)


class MonitorService:
    def __init__(self):
        self.alert_service = AlertService()
    
    def check_all_monitors(self):
        """Check all active monitors"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT id, name, url, timeout, alert_threshold
                FROM monitors
                WHERE is_active = TRUE
            """)
            
            monitors = cur.fetchall()
            logger.info(f"Checking {len(monitors)} active monitors...")
            
            for monitor in monitors:
                self.check_monitor(monitor)
                
        except Exception as e:
            logger.error(f"Error checking monitors: {str(e)}")
        finally:
            cur.close()
            conn.close()
    
    def check_monitor(self, monitor):
        """Check a single monitor"""
        monitor_id = monitor['id']
        name = monitor['name']
        url = monitor['url']
        timeout = monitor['timeout']
        
        try:
            # Perform HTTP request
            start_time = time.time()
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Determine if monitor is up
            is_up = 200 <= response.status_code < 400
            
            # Save metric
            self.save_metric(
                monitor_id=monitor_id,
                status_code=response.status_code,
                response_time=response_time,
                is_up=is_up,
                error_message=None
            )
            
            # Check if alert needed
            if not is_up:
                self.check_alert_condition(monitor)
            else:
                self.resolve_alerts(monitor_id)
            
            logger.info(f"✓ {name}: {response.status_code} ({response_time:.2f}ms)")
            
        except requests.exceptions.Timeout:
            self.handle_monitor_error(monitor, "Request timeout")
            logger.warning(f"✗ {name}: Timeout")
            
        except requests.exceptions.ConnectionError:
            self.handle_monitor_error(monitor, "Connection error")
            logger.warning(f"✗ {name}: Connection error")
            
        except Exception as e:
            self.handle_monitor_error(monitor, str(e))
            logger.error(f"✗ {name}: {str(e)}")
    
    def save_metric(self, monitor_id, status_code, response_time, is_up, error_message):
        """Save metric to database"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO metrics (monitor_id, status_code, response_time, is_up, error_message)
                VALUES (%s, %s, %s, %s, %s)
            """, (monitor_id, status_code, response_time, is_up, error_message))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving metric: {str(e)}")
        finally:
            cur.close()
            conn.close()
    
    def handle_monitor_error(self, monitor, error_message):
        """Handle monitor check error"""
        self.save_metric(
            monitor_id=monitor['id'],
            status_code=None,
            response_time=None,
            is_up=False,
            error_message=error_message
        )
        
        self.check_alert_condition(monitor)
    
    def check_alert_condition(self, monitor):
        """Check if alert should be triggered"""
        monitor_id = monitor['id']
        threshold = monitor['alert_threshold']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get last N checks
            cur.execute("""
                SELECT is_up
                FROM metrics
                WHERE monitor_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (monitor_id, threshold))
            
            recent_checks = cur.fetchall()
            
            # If we have enough failed checks, trigger alert
            if len(recent_checks) >= threshold:
                all_down = all(not check['is_up'] for check in recent_checks)
                
                if all_down:
                    # Check if there's already an active alert
                    cur.execute("""
                        SELECT id FROM alerts
                        WHERE monitor_id = %s AND status = 'active'
                    """, (monitor_id,))
                    
                    existing_alert = cur.fetchone()
                    
                    if not existing_alert:
                        self.alert_service.create_alert(
                            monitor_id=monitor_id,
                            monitor_name=monitor['name'],
                            alert_type='down',
                            message=f"Monitor '{monitor['name']}' is down. Failed {threshold} consecutive checks."
                        )
                        
        except Exception as e:
            logger.error(f"Error checking alert condition: {str(e)}")
        finally:
            cur.close()
            conn.close()
    
    def resolve_alerts(self, monitor_id):
        """Resolve active alerts for a monitor"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                UPDATE alerts
                SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
                WHERE monitor_id = %s AND status = 'active'
                RETURNING id, monitor_id
            """, (monitor_id,))
            
            resolved = cur.fetchall()
            conn.commit()
            
            for alert in resolved:
                logger.info(f"Resolved alert {alert['id']} for monitor {monitor_id}")
                # Could send resolution notification here
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error resolving alerts: {str(e)}")
        finally:
            cur.close()
            conn.close()
    
    def get_monitor_status(self, monitor_id):
        """Get current status of a monitor"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get latest metric
            cur.execute("""
                SELECT status_code, response_time, is_up, error_message, timestamp
                FROM metrics
                WHERE monitor_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (monitor_id,))
            
            latest = cur.fetchone()
            
            # Get uptime percentage (last 24 hours)
            cur.execute("""
                SELECT 
                    COUNT(*) as total_checks,
                    SUM(CASE WHEN is_up THEN 1 ELSE 0 END) as successful_checks
                FROM metrics
                WHERE monitor_id = %s 
                AND timestamp > NOW() - INTERVAL '24 hours'
            """, (monitor_id,))
            
            stats = cur.fetchone()
            
            uptime_percent = 0
            if stats['total_checks'] > 0:
                uptime_percent = (stats['successful_checks'] / stats['total_checks']) * 100
            
            return {
                'latest_check': dict(latest) if latest else None,
                'uptime_24h': round(uptime_percent, 2),
                'total_checks_24h': stats['total_checks']
            }
            
        except Exception as e:
            logger.error(f"Error getting monitor status: {str(e)}")
            return None
        finally:
            cur.close()
            conn.close()
