"""
Alert Routes
API endpoints for managing alerts
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from utils.database import get_db_connection

logger = logging.getLogger(__name__)
alert_bp = Blueprint('alerts', __name__)


@alert_bp.route('', methods=['GET'])
def get_alerts():
    """Get alerts with optional filtering"""
    try:
        # Get query parameters
        monitor_id = request.args.get('monitor_id', type=int)
        status = request.args.get('status')  # active, resolved
        limit = request.args.get('limit', default=50, type=int)
        
        if limit > 500:
            limit = 500
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build query
        query = """
            SELECT a.id, a.monitor_id, m.name as monitor_name,
                   a.alert_type, a.message, a.status, a.acknowledged,
                   a.acknowledged_at, a.created_at, a.resolved_at
            FROM alerts a
            JOIN monitors m ON a.monitor_id = m.id
            WHERE 1=1
        """
        params = []
        
        if monitor_id:
            query += " AND a.monitor_id = %s"
            params.append(monitor_id)
        
        if status:
            query += " AND a.status = %s"
            params.append(status)
        
        query += " ORDER BY a.created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        alerts = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify([dict(a) for a in alerts]), 200
        
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/<int:alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Get a specific alert"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT a.id, a.monitor_id, m.name as monitor_name,
                   a.alert_type, a.message, a.status, a.acknowledged,
                   a.acknowledged_at, a.created_at, a.resolved_at
            FROM alerts a
            JOIN monitors m ON a.monitor_id = m.id
            WHERE a.id = %s
        """, (alert_id,))
        
        alert = cur.fetchone()
        cur.close()
        conn.close()
        
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        return jsonify(dict(alert)), 200
        
    except Exception as e:
        logger.error(f"Error getting alert: {str(e)}")
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE alerts
            SET acknowledged = TRUE, acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = %s AND acknowledged = FALSE
            RETURNING id, monitor_id, alert_type, message, status, 
                      acknowledged, acknowledged_at
        """, (alert_id,))
        
        alert = cur.fetchone()
        
        if not alert:
            cur.close()
            conn.close()
            return jsonify({'error': 'Alert not found or already acknowledged'}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Alert {alert_id} acknowledged")
        return jsonify(dict(alert)), 200
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/stats', methods=['GET'])
def get_alert_stats():
    """Get alert statistics"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        
        if hours > 720:
            hours = 720
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get overall stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_alerts,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_alerts,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_alerts,
                SUM(CASE WHEN acknowledged THEN 1 ELSE 0 END) as acknowledged_alerts
            FROM alerts
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (hours,))
        
        stats = cur.fetchone()
        
        # Get alerts by monitor
        cur.execute("""
            SELECT m.name, COUNT(*) as alert_count
            FROM alerts a
            JOIN monitors m ON a.monitor_id = m.id
            WHERE a.created_at > NOW() - INTERVAL '%s hours'
            GROUP BY m.name
            ORDER BY alert_count DESC
        """, (hours,))
        
        by_monitor = cur.fetchall()
        
        cur.close()
        conn.close()
        
        result = dict(stats)
        result['by_monitor'] = [dict(m) for m in by_monitor]
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting alert stats: {str(e)}")
        return jsonify({'error': str(e)}), 500