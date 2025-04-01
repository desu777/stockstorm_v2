# StockStorm Performance Optimization Deployment Guide

This guide outlines the steps needed to deploy the performance optimizations to your StockStorm service.

## 1. Prerequisites

- Ubuntu/Debian server running your StockStorm application
- Root or sudo access to the server
- Python 3.8+ and pip

## 2. Install Dependencies

```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Enable and start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Install Python dependencies
cd /root/stockstorm-1/
pip install -r requirements.txt
```

## 3. Copy Optimized Files to Server

Copy all the modified files to your server:

- `v1/stockstorm_project/settings.py` (replace with optimized version)
- `v1/stockstorm_project/__init__.py`
- `v1/stockstorm_project/celery.py` (new file)
- `v1/home/tasks.py` (new file)
- `v1/home/middleware.py`
- `v1/home/sync_bot_middleware.py`

## 4. Set Up Celery Services

```bash
# Copy service files to systemd
sudo cp celery.service /etc/systemd/system/
sudo cp celerybeat.service /etc/systemd/system/

# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Enable and start Celery services
sudo systemctl enable celery.service
sudo systemctl enable celerybeat.service
sudo systemctl start celery.service
sudo systemctl start celerybeat.service
```

## 5. Verify Services

```bash
# Check Redis status
sudo systemctl status redis-server

# Check Celery worker status
sudo systemctl status celery.service

# Check Celery beat status
sudo systemctl status celerybeat.service
```

## 6. Configure Nginx (Optional but Recommended)

If you're using Nginx, make sure to configure it for static file serving:

```bash
# Example Nginx configuration snippet for static files
location /static/ {
    alias /root/stockstorm-1/v1/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, max-age=2592000";
}
```

## 7. Restart Web Service

```bash
# If using Gunicorn with systemd
sudo systemctl restart gunicorn

# If using another method, restart your Django application accordingly
```

## 8. Monitor Performance

After deploying, monitor the performance to ensure improvements are effective:

- Check CPU and memory usage with `htop`
- Monitor Redis usage with `redis-cli info`
- Check Celery task queue with `celery -A stockstorm_project inspect active`

## Troubleshooting

### Redis Connection Issues

If you encounter Redis connection issues:

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Check if Redis is accessible
redis-cli ping
```

### Celery Worker Issues

If Celery workers are not running:

```bash
# Check Celery logs
sudo journalctl -u celery.service

# Start Celery in foreground for debugging
cd /root/stockstorm-1/v1
celery -A stockstorm_project worker --loglevel=debug
```

### Application Performance Issues

If the application still has performance issues:

1. Check Django logs for errors
2. Enable DEBUG temporarily to identify bottlenecks
3. Use Django Debug Toolbar in development to find slow queries 