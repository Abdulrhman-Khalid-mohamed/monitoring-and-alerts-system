
"""
Input Validation Utilities
Validates and sanitizes user input
"""

import re
from urllib.parse import urlparse


def validate_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False


def validate_monitor_data(data):
    """Validate monitor creation/update data"""
    errors = []
    
    # Required fields for creation
    if 'name' in data:
        if not data['name'] or len(data['name'].strip()) == 0:
            errors.append("Name is required")
        elif len(data['name']) > 255:
            errors.append("Name must be less than 255 characters")
    
    if 'url' in data:
        if not data['url']:
            errors.append("URL is required")
        elif not validate_url(data['url']):
            errors.append("Invalid URL format")
        elif len(data['url']) > 512:
            errors.append("URL must be less than 512 characters")
    
    # Optional fields validation
    if 'check_interval' in data:
        try:
            interval = int(data['check_interval'])
            if interval < 10:
                errors.append("Check interval must be at least 10 seconds")
            elif interval > 86400:
                errors.append("Check interval must be less than 24 hours")
        except (ValueError, TypeError):
            errors.append("Check interval must be a valid integer")
    
    if 'timeout' in data:
        try:
            timeout = int(data['timeout'])
            if timeout < 1:
                errors.append("Timeout must be at least 1 second")
            elif timeout > 300:
                errors.append("Timeout must be less than 5 minutes")
        except (ValueError, TypeError):
            errors.append("Timeout must be a valid integer")
    
    if 'alert_threshold' in data:
        try:
            threshold = int(data['alert_threshold'])
            if threshold < 1:
                errors.append("Alert threshold must be at least 1")
            elif threshold > 100:
                errors.append("Alert threshold must be less than 100")
        except (ValueError, TypeError):
            errors.append("Alert threshold must be a valid integer")
    
    if 'monitor_type' in data:
        valid_types = ['http', 'https', 'api']
        if data['monitor_type'] not in valid_types:
            errors.append(f"Monitor type must be one of: {', '.join(valid_types)}")
    
    return errors


def sanitize_string(text, max_length=None):
    """Sanitize string input"""
    if not text:
        return ""
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_time_range(start_time, end_time):
    """Validate time range parameters"""
    from datetime import datetime
    
    errors = []
    
    try:
        if start_time:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if end_time:
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
        if start_time and end_time:
            if start >= end:
                errors.append("Start time must be before end time")
    except ValueError:
        errors.append("Invalid datetime format. Use ISO 8601 format")
    
    return errors
