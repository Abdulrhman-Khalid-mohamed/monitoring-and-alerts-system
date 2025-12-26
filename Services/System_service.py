"""
System Service
Monitors local system resources (CPU, memory, disk)
"""

import psutil
import logging
from utils.database import get_db_connection

logger = logging.getLogger(__name__)


class SystemService:
    def collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory info
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024 ** 3)
            memory_total_gb = memory.total / (1024 ** 3)
            
            # Get disk info
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024 ** 3)
            disk_total_gb = disk.total / (1024 ** 3)
            
            # Save to database
            self.save_system_metrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_gb=memory_used_gb,
                memory_total_gb=memory_total_gb,
                disk_percent=disk_percent,
                disk_used_gb=disk_used_gb,
                disk_total_gb=disk_total_gb
            )
            
            logger.info(f"System metrics: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%")
            
            return {
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory_percent, 2),
                'memory_used_gb': round(memory_used_gb, 2),
                'memory_total_gb': round(memory_total_gb, 2),
                'disk_percent': round(disk_percent, 2),
                'disk_used_gb': round(disk_used_gb, 2),
                'disk_total_gb': round(disk_total_gb, 2)
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return None
    
    def save_system_metrics(self, cpu_percent, memory_percent, memory_used_gb, 
                           memory_total_gb, disk_percent, disk_used_gb, disk_total_gb):
        """Save system metrics to database"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO system_metrics 
                (cpu_percent, memory_percent, memory_used_gb, memory_total_gb,
                 disk_percent, disk_used_gb, disk_total_gb)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (cpu_percent, memory_percent, memory_used_gb, memory_total_gb,
                  disk_percent, disk_used_gb, disk_total_gb))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving system metrics: {str(e)}")
        finally:
            cur.close()
            conn.close()
    
    def get_current_metrics(self):
        """Get current system metrics without saving"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {
                    'percent': round(cpu_percent, 2),
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'percent': round(memory.percent, 2),
                    'used_gb': round(memory.used / (1024 ** 3), 2),
                    'total_gb': round(memory.total / (1024 ** 3), 2),
                    'available_gb': round(memory.available / (1024 ** 3), 2)
                },
                'disk': {
                    'percent': round(disk.percent, 2),
                    'used_gb': round(disk.used / (1024 ** 3), 2),
                    'total_gb': round(disk.total / (1024 ** 3), 2),
                    'free_gb': round(disk.free / (1024 ** 3), 2)
                }
            }
        except Exception as e:
            logger.error(f"Error getting current metrics: {str(e)}")
            return None
    
    def get_historical_metrics(self, hours=24):
        """Get historical system metrics"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    cpu_percent, memory_percent, disk_percent,
                    memory_used_gb, memory_total_gb,
                    disk_used_gb, disk_total_gb,
                    timestamp
                FROM system_metrics
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                ORDER BY timestamp DESC
            """, (hours,))
            
            metrics = cur.fetchall()
            return [dict(m) for m in metrics]
            
        except Exception as e:
            logger.error(f"Error getting historical metrics: {str(e)}")
            return []
        finally:
            cur.close()
            conn.close()
