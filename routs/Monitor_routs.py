"""
Monitor Routes
API endpoints for managing monitors
"""

from flask import Blueprint, request, jsonify
import logging
from utils.database import get_db_connection
from utils.validators import validate_monitor_data, sanitize_string
from services.monitor_service import MonitorService

logger = logging.getLogger(__name__)
monitor_bp = Blueprint('monitors', __name__)
monitor_service = MonitorService()


@monitor_bp.route('', methods=['GET'])
def get_monitors():
    """Get all monitors"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, name, url, monitor_type, check_interval, timeout, 
                   alert_threshold, is_active, created_at, updated_at
            FROM monitors
            ORDER BY created_at DESC
        """)
        
        monitors = cur.fetchall()
        
        # Get status for each monitor
        result = []
        for monitor in monitors:
            monitor_dict = dict(monitor)
            status = monitor_service.get_monitor_status(monitor['id'])
            monitor_dict['status'] = status
            result.append(monitor_dict)
        
        cur.close()
        conn.close()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting monitors: {str(e)}")
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/<int:monitor_id>', methods=['GET'])
def get_monitor(monitor_id):
    """Get a specific monitor"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, name, url, monitor_type, check_interval, timeout,
                   alert_threshold, is_active, created_at, updated_at
            FROM monitors
            WHERE id = %s
        """, (monitor_id,))
        
        monitor = cur.fetchone()
        cur.close()
        conn.close()
        
        if not monitor:
            return jsonify({'error': 'Monitor not found'}), 404
        
        monitor_dict = dict(monitor)
        status = monitor_service.get_monitor_status(monitor_id)
        monitor_dict['status'] = status
        
        return jsonify(monitor_dict), 200
        
    except Exception as e:
        logger.error(f"Error getting monitor: {str(e)}")
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('', methods=['POST'])
def create_monitor():
    """Create a new monitor"""
    try:
        data = request.get_json()
        
        # Validate input
        errors = validate_monitor_data(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        # Sanitize inputs
        name = sanitize_string(data.get('name'), 255)
        url = sanitize_string(data.get('url'), 512)
        monitor_type = data.get('monitor_type', 'http')
        check_interval = data.get('check_interval', 60)
        timeout = data.get('timeout', 10)
        alert_threshold = data.get('alert_threshold', 3)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO monitors (name, url, monitor_type, check_interval, timeout, alert_threshold)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, url, monitor_type, check_interval, timeout, 
                      alert_threshold, is_active, created_at, updated_at
        """, (name, url, monitor_type, check_interval, timeout, alert_threshold))
        
        monitor = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Created monitor: {name}")
        return jsonify(dict(monitor)), 201
        
    except Exception as e:
        logger.error(f"Error creating monitor: {str(e)}")
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/<int:monitor_id>', methods=['PUT'])
def update_monitor(monitor_id):
    """Update a monitor"""
    try:
        data = request.get_json()
        
        # Validate input
        errors = validate_monitor_data(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if 'name' in data:
            update_fields.append('name = %s')
            params.append(sanitize_string(data['name'], 255))
        
        if 'url' in data:
            update_fields.append('url = %s')
            params.append(sanitize_string(data['url'], 512))
        
        if 'monitor_type' in data:
            update_fields.append('monitor_type = %s')
            params.append(data['monitor_type'])
        
        if 'check_interval' in data:
            update_fields.append('check_interval = %s')
            params.append(data['check_interval'])
        
        if 'timeout' in data:
            update_fields.append('timeout = %s')
            params.append(data['timeout'])
        
        if 'alert_threshold' in data:
            update_fields.append('alert_threshold = %s')
            params.append(data['alert_threshold'])
        
        if 'is_active' in data:
            update_fields.append('is_active = %s')
            params.append(data['is_active'])
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        params.append(monitor_id)
        
        query = f"""
            UPDATE monitors 
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, name, url, monitor_type, check_interval, timeout,
                      alert_threshold, is_active, created_at, updated_at
        """
        
        cur.execute(query, params)
        monitor = cur.fetchone()
        
        if not monitor:
            cur.close()
            conn.close()
            return jsonify({'error': 'Monitor not found'}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Updated monitor: {monitor_id}")
        return jsonify(dict(monitor)), 200
        
    except Exception as e:
        logger.error(f"Error updating monitor: {str(e)}")
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/<int:monitor_id>', methods=['DELETE'])
def delete_monitor(monitor_id):
    """Delete a monitor"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('DELETE FROM monitors WHERE id = %s RETURNING id', (monitor_id,))
        deleted = cur.fetchone()
        
        if not deleted:
            cur.close()
            conn.close()
            return jsonify({'error': 'Monitor not found'}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Deleted monitor: {monitor_id}")
        return jsonify({'message': 'Monitor deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting monitor: {str(e)}")
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/<int:monitor_id>/check', methods=['POST'])
def check_monitor_now(monitor_id):
    """Manually trigger a monitor check"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, name, url, timeout, alert_threshold
            FROM monitors
            WHERE id = %s
        """, (monitor_id,))
        
        monitor = cur.fetchone()
        cur.close()
        conn.close()
        
        if not monitor:
            return jsonify({'error': 'Monitor not found'}), 404
        
        # Run check
        monitor_service.check_monitor(monitor)
        
        return jsonify({'message': 'Monitor check completed'}), 200
        
    except Exception as e:
        logger.error(f"Error checking monitor: {str(e)}")
        return jsonify({'error': str(e)}), 500
