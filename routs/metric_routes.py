"""
Metric Routes
API endpoints for querying metrics data
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from utils.database import get_db_connection
from utils.validators import validate_time_range

logger = logging.getLogger(__name__)
metric_bp = Blueprint('metrics', __name__)


@metric_bp.route('', methods=['GET'])
def get_metrics():
    """Get metrics with optional filtering"""
    try:
        # Get query parameters
        monitor_id = request.args.get('monitor_id', type=int)
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = request.args.get('limit', default=100, type=int)
        
        # Validate time range if provided
        if start_time or end_time:
            errors = validate_time_range(start_time, end_time)
            if errors:
                return jsonify({'error': 'Invalid time range', 'details': errors}), 400
        
        # Limit maximum results
        if limit > 1000:
            limit = 1000
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build query
        query = """
            SELECT m.id, m.monitor_id, mon.name as monitor_name,
                   m.status_code, m.response_time, m.is_up, 
                   m.error_message, m.timestamp
            FROM metrics m
            JOIN monitors mon ON m.monitor_id = mon.id
            WHERE 1=1
        """
        params = []
        
        if monitor_id:
            query += " AND m.monitor_id = %s"
            params.append(monitor_id)
        
        if start_time:
            query += " AND m.timestamp >= %s"
            params.append(start_time)
        
        if end_time:
            query += " AND m.timestamp <= %s"
            params.append(end_time)
        
        query += " ORDER BY m.timestamp DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        metrics = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify([dict(m) for m in metrics]), 200
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@metric_bp.route('/summary', methods=['GET'])
def get_metrics_summary():
    """Get summary statistics for metrics"""
    try:
        monitor_id = request.args.get('monitor_id', type=int)
        hours = request.args.get('hours', default=24, type=int)
        
        if hours > 720:  # Max 30 days
            hours = 720
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                COUNT(*) as total_checks,
                SUM(CASE WHEN is_up THEN 1 ELSE 0 END) as successful_checks,
                SUM(CASE WHEN NOT is_up THEN 1 ELSE 0 END) as failed_checks,
                AVG(response_time) as avg_response_time,
                MIN(response_time) as min_response_time,
                MAX(response_time) as max_response_time
            FROM metrics
            WHERE timestamp > NOW() - INTERVAL '%s hours'
        """
        params = [hours]
        
        if monitor_id:
            query += " AND monitor_id = %s"
            params.append(monitor_id)
        
        cur.execute(query, params)
        summary = cur.fetchone()
        
        cur.close()
        conn.close()
        
        result = dict(summary)
        
        # Calculate uptime percentage
        if result['total_checks'] > 0:
            result['uptime_percent'] = round(
                (result['successful_checks'] / result['total_checks']) * 100, 2
            )
        else:
            result['uptime_percent'] = 0
        
        # Round response times
        if result['avg_response_time']:
            result['avg_response_time'] = round(result['avg_response_time'], 2)
        if result['min_response_time']:
            result['min_response_time'] = round(result['min_response_time'], 2)
        if result['max_response_time']:
            result['max_response_time'] = round(result['max_response_time'], 2)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {str(e)}")
        return jsonify({'error': str(e)}), 500


@metric_bp.route('/system', methods=['GET'])
def get_system_metrics():
    """Get system resource metrics"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        limit = request.args.get('limit', default=100, type=int)
        
        if hours > 720:
            hours = 720
        if limit > 1000:
            limit = 1000
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, cpu_percent, memory_percent, disk_percent,
                   memory_used_gb, memory_total_gb, disk_used_gb, 
                   disk_total_gb, timestamp
            FROM system_metrics
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC
            LIMIT %s
        """, (hours, limit))
        
        metrics = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify([dict(m) for m in metrics]), 200
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500