# HOSPlanner Django API

A Django REST Framework (DRF) project with a simple health check API endpoint.

## Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run migrations:

```bash
python manage.py migrate
```

4. Start the development server:

```bash
python manage.py runserver
```

## API Endpoints

### Health Check

- **URL**: `GET /api/health/`
- **Description**: Simple health check endpoint to confirm the API is working
- **Response**: JSON with status, message, and service information

Example response:

```json
{
  "status": "success",
  "message": "HOSPlanner API is working!",
  "data": {
    "service": "HOSPlanner",
    "version": "1.0.0",
    "status": "healthy"
  }
}
```

## Testing the API

You can test the API using curl:

```bash
curl http://localhost:8000/api/health/
```

Or visit in your browser:
http://localhost:8000/api/health/

## Project Structure

- `hosplanner/` - Main Django project settings
- `api/` - API application with views and URL patterns
- `requirements.txt` - Python dependencies
- `manage.py` - Django management script
