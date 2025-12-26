"""
Unit tests for monitor functionality
"""

import pytest
import json
from app import app
from utils.database import init_db


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    """Test root endpoint"""
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'name' in data
    assert data['status'] == 'running'


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code in [200, 503]


def test_create_monitor(client):
    """Test creating a monitor"""
    monitor_data = {
        'name': 'Test Monitor',
        'url': 'https://example.com',
        'check_interval': 60,
        'timeout': 10
    }
    
    response = client.post(
        '/api/monitors',
        data=json.dumps(monitor_data),
        content_type='application/json'
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'Test Monitor'
    assert data['url'] == 'https://example.com'


def test_create_monitor_invalid_url(client):
    """Test creating monitor with invalid URL"""
    monitor_data = {
        'name': 'Test Monitor',
        'url': 'not-a-valid-url',
        'check_interval': 60
    }
    
    response = client.post(
        '/api/monitors',
        data=json.dumps(monitor_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_get_monitors(client):
    """Test getting all monitors"""
    response = client.get('/api/monitors')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_get_metrics(client):
    """Test getting metrics"""
    response = client.get('/api/metrics?limit=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_get_alerts(client):
    """Test getting alerts"""
    response = client.get('/api/alerts?limit=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_uptime_analytics(client):
    """Test uptime analytics endpoint"""
    response = client.get('/api/analytics/uptime?days=7')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'period_days' in data
    assert 'monitors' in data