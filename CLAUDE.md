# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `btppg-driver`, a Flask-based Python application designed as a PostgreSQL database driver for SAP BTP and Kyma environments. The application provides REST API endpoints for database operations and file imports, with support for various file formats (CSV, Excel, JSON).

## Development Commands

### Running the Application
```bash
# Local development
python run.py

# Production with Gunicorn
gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --preload wsgi:app
```

### Testing
```bash
# Test database connection
python -c "from app.main import create_app; app = create_app(); print('DB test:', app.db_manager.test_connection())"

# Test import functionality
python test_batch_import.py
python test_batch_local.py
```

### Docker
```bash
# Build image
docker build -t btppg-driver .

# Run container
docker run -p 8080:8080 --env-file .env btppg-driver
```

### Kubernetes/Kyma Deployment
```bash
# Deploy to Kyma
kubectl apply -f deployment.yaml

# Check deployment status
kubectl get pods -l app=btppg-driver
kubectl logs -l app=btppg-driver
```

## Architecture

### Core Components

- **Flask Application Factory** (`app/main.py`): Creates and configures the Flask app with database manager and blueprints
- **Database Manager** (`app/database.py`): ThreadedConnectionPool-based PostgreSQL connection management optimized for Kyma/Kubernetes environments
- **Configuration System** (`app/config.py`): Handles both SAP BTP VCAP_SERVICES and environment variable-based configuration
- **Import Service** (`services/import_service.py`): Bulk file import functionality with CSV/Excel/JSON support
- **Security Service** (`services/security_service.py`): Authentication and security utilities

### API Structure

The application uses Flask Blueprints with the following main endpoints:

- `/api/import/<table_name>` - File upload and import functionality
- `/api/tables` - Database table management
- `/api/status` - Application and database status
- `/health` - Kubernetes health check endpoint

### Database Architecture

- Uses PostgreSQL with connection pooling (ThreadedConnectionPool)
- Optimized for Kyma/Kubernetes networking with keep-alive settings
- Supports both SAP BTP managed PostgreSQL and external providers (currently configured for Neon)
- Automatic retry logic and connection health checks

## Configuration

### Environment Variables

Key environment variables (see `.env` for full configuration):

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Flask secret key
- `FLASK_DEBUG` - Debug mode (true/false)
- `PORT` - Application port (default: 5000)
- `MAX_CONTENT_LENGTH` - File upload limit

### SAP BTP Integration

The application automatically detects SAP BTP Cloud Foundry environments via `VCAP_SERVICES` and can configure database connections accordingly.

## File Processing

The import service supports:
- **CSV files**: Standard comma-separated values
- **Excel files**: .xlsx and .xls formats
- **JSON files**: Array of objects or single object format

Import operations use optimized bulk insert/update strategies with batch processing for large datasets.

## Development Notes

- The application uses Hungarian comments and logging messages in many places
- Database operations are optimized for bulk processing (1000-record batches)
- Connection pooling is configured for Kubernetes environments with appropriate timeouts
- Error handling includes retry logic and automatic pool reinitialization
- The application follows a service-layer architecture pattern

## Monitoring and Debugging

- Health check endpoint: `/health`
- Database connection test: `/test-db`
- Pool status debugging available via `DatabaseManager.get_pool_status()`
- Comprehensive logging throughout the application