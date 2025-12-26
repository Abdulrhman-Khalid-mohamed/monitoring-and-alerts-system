## Features

- **Website Uptime Monitoring** - Check HTTP/HTTPS endpoints at configurable intervals
- **API Performance Tracking** - Monitor response times and status codes
- **System Resource Monitoring** - Track CPU, memory, and disk usage
- **Alert System** - Email and Slack notifications when thresholds are breached
- **Historical Data** - Store all metrics in PostgreSQL for trend analysis
- **REST API** - Full API for managing monitors and querying metrics
- **Dashboard Data** - Endpoints for building custom dashboards

## Tech Stack

- **Backend**: Python 3.8+, Flask
- **Database**: PostgreSQL
- **Monitoring**: psutil, requests
- **Notifications**: SMTP (email), Slack webhooks
- **Scheduling**: APScheduler
- **Data Processing**: Pandas (for analytics)

## Installation

### Prerequisites

```bash
# Install Python 3.8 or higher
python3 --version

# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian
# or
brew install postgresql  # macOS
```

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/system-monitor.git
cd system-monitor
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create PostgreSQL database:
```bash
sudo -u postgres psql
CREATE DATABASE monitor_db;
CREATE USER monitor_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE monitor_db TO monitor_user;
\q
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

6. Initialize database:
```bash
python init_db.py
```

7. Run the application:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## Configuration

Edit `.env` file:

```env
# Database
DATABASE_URL=postgresql://monitor_user:your_password@localhost/monitor_db

# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Email Alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=admin@yourdomain.com

# Slack Alerts (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Monitoring Settings
CHECK_INTERVAL=60  # seconds
ALERT_COOLDOWN=300  # seconds between repeated alerts
```

## API Documentation

### Monitors

**Create Monitor**
```bash
POST /api/monitors
Content-Type: application/json

{
  "name": "Main Website",
  "url": "https://example.com",
  "check_interval": 60,
  "timeout": 10,
  "alert_threshold": 3
}
```

**List Monitors**
```bash
GET /api/monitors
```

**Get Monitor Details**
```bash
GET /api/monitors/{id}
```

**Update Monitor**
```bash
PUT /api/monitors/{id}
Content-Type: application/json

{
  "name": "Updated Name",
  "check_interval": 120
}
```

**Delete Monitor**
```bash
DELETE /api/monitors/{id}
```

### Metrics

**Get Latest Metrics**
```bash
GET /api/metrics?monitor_id={id}&limit=100
```

**Get Metrics by Time Range**
```bash
GET /api/metrics?monitor_id={id}&start_time=2025-01-01T00:00:00&end_time=2025-01-02T00:00:00
```

**Get System Metrics**
```bash
GET /api/system/metrics
```

### Alerts

**Get Active Alerts**
```bash
GET /api/alerts?status=active
```

**Get Alert History**
```bash
GET /api/alerts?monitor_id={id}&limit=50
```

**Acknowledge Alert**
```bash
POST /api/alerts/{id}/acknowledge
```

### Analytics

**Get Uptime Statistics**
```bash
GET /api/analytics/uptime?monitor_id={id}&days=7
```

**Get Performance Report**
```bash
GET /api/analytics/performance?monitor_id={id}
```

## Usage Examples

### Monitor a Website

```python
import requests

# Create a monitor
response = requests.post('http://localhost:5000/api/monitors', json={
    'name': 'My Website',
    'url': 'https://mywebsite.com',
    'check_interval': 60,
    'timeout': 10
})

monitor = response.json()
print(f"Monitor created with ID: {monitor['id']}")

# Get latest metrics
metrics = requests.get(f"http://localhost:5000/api/metrics?monitor_id={monitor['id']}")
print(metrics.json())
```

### System Resource Monitoring

The system automatically monitors local resources. Access via:

```bash
curl http://localhost:5000/api/system/metrics
```

## Project Structure

```
system-monitor/
├── app.py                 # Main Flask application
├── init_db.py            # Database initialization
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
├── config/
│   └── config.py         # Configuration management
├── models/
│   ├── __init__.py
│   ├── monitor.py        # Monitor model
│   ├── metric.py         # Metric model
│   └── alert.py          # Alert model
├── services/
│   ├── __init__.py
│   ├── monitor_service.py    # Monitoring logic
│   ├── alert_service.py      # Alert notifications
│   └── system_service.py     # System metrics
├── routes/
│   ├── __init__.py
│   ├── monitor_routes.py     # Monitor endpoints
│   ├── metric_routes.py      # Metric endpoints
│   ├── alert_routes.py       # Alert endpoints
│   └── analytics_routes.py   # Analytics endpoints
├── utils/
│   ├── __init__.py
│   ├── database.py       # Database utilities
│   └── validators.py     # Input validation
└── tests/
    ├── __init__.py
    ├── test_monitors.py
    ├── test_alerts.py
    └── test_api.py
```

## Running Tests

```bash
pytest tests/
```

## Deployment

### Using Docker

```bash
docker-compose up -d
```

### Manual Deployment

1. Set up production PostgreSQL database
2. Configure environment variables for production
3. Use gunicorn for production server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

4. Set up nginx as reverse proxy
5. Configure systemd service for auto-start

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub.

## Roadmap

- [ ] Web dashboard UI
- [ ] Docker container support
- [ ] Prometheus integration
- [ ] Custom alert rules engine
- [ ] Mobile app notifications
- [ ] SSL certificate monitoring
- [ ] DNS monitoring
- [ ] Port monitoring
- [ ] Multi-region checks
