"""
Analytics Routes
API endpoints for analytics and reporting
"""

from flask import Blueprint, request, jsonify
import logging
import pandas as pd
from utils.database import get_db_connection

logger = logging.getLogger(__name__)
analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/uptime', methods=['GET'])
def get_uptime_report():
    """Get uptime report for monitors"""
    try:
        monitor_id = request.args.get('monitor_id', type=int)
        days = request.args.get('days', default=7, type=int)
        
        if days > 90:
            days = 90
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get uptime data
        query = """
            SELECT 
                m.id, m.name,
                COUNT(*) as total_checks,
                SUM(CASE WHEN met.is_up THEN 1 ELSE 0 END) as successful_checks,
                AVG(met.response_time) as avg_response_time
            FROM monitors m
            LEFT JOIN metrics met ON m.id = met.monitor_id
            WHERE met.timestamp > NOW() - INTERVAL '%s days'
        """
        params = [days]
        
        if monitor_id:
            query += " AND m.id = %s"
            params.append(monitor_id)
        
        query += " GROUP BY m.id, m.name ORDER BY m.name"
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Calculate uptime percentages
        report = []
        for row in results:
            uptime_percent = 0
            if row['total_checks'] > 0:
                uptime_percent = (row['successful_checks'] / row['total_checks']) * 100
            
            report.append({
                'monitor_id': row['id'],
                'monitor_name': row['name'],
                'total_checks': row['total_checks'],
                'successful_checks': row['successful_checks'],
                'failed_checks': row['total_checks'] - row['successful_checks'],
                'uptime_percent': round(uptime_percent, 2),
                'avg_response_time': round(row['avg_response_time'], 2) if row['avg_response_time'] else None
            })
        
        return jsonify({
            'period_days': days,
            'monitors': report
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating uptime report: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/performance', methods=['GET'])
def get_performance_report():
    """Get performance report with response time trends"""
    try:
        monitor_id = request.args.get('monitor_id', type=int)
        hours = request.args.get('hours', default=24, type=int)
        
        if not monitor_id:
            return jsonify({'error': 'monitor_id is required'}), 400
        
        if hours > 720:
            hours = 720
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get response time data
        cur.execute("""
            SELECT response_time, timestamp, is_up
            FROM metrics
            WHERE monitor_id = %s 
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND response_time IS NOT NULL
            ORDER BY timestamp
        """, (monitor_id, hours))
        
        metrics = cur.fetchall()
        cur.close()
        conn.close()
        
        if not metrics:
            return jsonify({'error': 'No data available for this monitor'}), 404
        
        # Convert to pandas for analysis
        df = pd.DataFrame([dict(m) for m in metrics])
        
        # Calculate statistics
        stats = {
            'monitor_id': monitor_id,
            'period_hours': hours,
            'total_requests': len(df),
            'successful_requests': int(df['is_up'].sum()),
            'response_time': {
                'min': round(df['response_time'].min(), 2),
                'max': round(df['response_time'].max(), 2),
                'avg': round(df['response_time'].mean(), 2),
                'median': round(df['response_time'].median(), 2),
                'p95': round(df['response_time'].quantile(0.95), 2),
                'p99': round(df['response_time'].quantile(0.99), 2)
            }
        }
        
        # Get hourly averages
        df['hour'] = pd.to_datetime(df['timestamp']).dt.floor('H')
        hourly = df.groupby('hour').agg({
            'response_time': 'mean',
            'is_up': 'sum'
        }).reset_index()
        
        stats['hourly_data'] = [
            {
                'hour': row['hour'].isoformat(),
                'avg_response_time': round(row['response_time'], 2),
                'successful_checks': int(row['is_up'])
            }
            for _, row in hourly.iterrows()
        ]
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error generating performance report: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/trends', methods=['GET'])
def get_trends():
    """Get trending data for all monitors"""
    try:
        days = request.args.get('days', default=7, type=int)
        
        if days > 90:
            days = 90
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get daily metrics
        cur.execute("""
            SELECT 
                m.id, m.name,
                DATE(met.timestamp) as date,
                COUNT(*) as total_checks,
                SUM(CASE WHEN met.is_up THEN 1 ELSE 0 END) as successful_checks,
                AVG(met.response_time) as avg_response_time
            FROM monitors m
            LEFT JOIN metrics met ON m.id = met.monitor_id
            WHERE met.timestamp > NOW() - INTERVAL '%s days'
            GROUP BY m.id, m.name, DATE(met.timestamp)
            ORDER BY m.id, date
        """, (days,))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        # Organize by monitor
        monitors = {}
        for row in results:
            monitor_id = row['id']
            if monitor_id not in monitors:
                monitors[monitor_id] = {
                    'monitor_id': monitor_id,
                    'monitor_name': row['name'],
                    'daily_stats': []
                }
            
            uptime = 0
            if row['total_checks'] > 0:
                uptime = (row['successful_checks'] / row['total_checks']) * 100
            
            monitors[monitor_id]['daily_stats'].append({
                'date': row['date'].isoformat(),
                'total_checks': row['total_checks'],
                'uptime_percent': round(uptime, 2),
                'avg_response_time': round(row['avg_response_time'], 2) if row['avg_response_time'] else None
            })
        
        return jsonify({
            'period_days': days,
            'monitors': list(monitors.values())
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating trends: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/system/trends', methods=['GET'])
def get_system_trends():
    """Get system resource trends"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        
        if hours > 720:
            hours = 720
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT cpu_percent, memory_percent, disk_percent, timestamp
            FROM system_metrics
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            ORDER BY timestamp
        """, (hours,))
        
        metrics = cur.fetchall()
        cur.close()
        conn.close()
        
        if not metrics:
            return jsonify({'error': 'No system metrics available'}), 404
        
        # Convert to pandas
        df = pd.DataFrame([dict(m) for m in metrics])
        
        # Calculate statistics
        stats = {
            'period_hours': hours,
            'cpu': {
                'min': round(df['cpu_percent'].min(), 2),
                'max': round(df['cpu_percent'].max(), 2),
                'avg': round(df['cpu_percent'].mean(), 2)
            },
            'memory': {
                'min': round(df['memory_percent'].min(), 2),
                'max': round(df['memory_percent'].max(), 2),
                'avg': round(df['memory_percent'].mean(), 2)
            },
            'disk': {
                'min': round(df['disk_percent'].min(), 2),
                'max': round(df['disk_percent'].max(), 2),
                'avg': round(df['disk_percent'].mean(), 2)
            }
        }
        
        # Get hourly averages
        df['hour'] = pd.to_datetime(df['timestamp']).dt.floor('H')
        hourly = df.groupby('hour').agg({
            'cpu_percent': 'mean',
            'memory_percent': 'mean',
            'disk_percent': 'mean'
        }).reset_index()
        
        stats['hourly_data'] = [
            {
                'hour': row['hour'].isoformat(),
                'cpu_percent': round(row['cpu_percent'], 2),
                'memory_percent': round(row['memory_percent'], 2),
                'disk_percent': round(row['disk_percent'], 2)
            }
            for _, row in hourly.iterrows()
        ]
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error generating system trends: {str(e)}")
        return jsonify({'error': str(e)}), 500