# ELD Trip Planner API

This Django REST API provides ELD (Electronic Logging Device) trip planning functionality with HOS (Hours of Service) compliance checking.

## Features

- **Google Maps Integration**: Uses Google Maps Directions API for real route data
- **HOS Compliance**: Enforces 70-hour cycle, 11-hour driving limits, break requirements
- **ELD Log Generation**: Creates realistic daily logs with proper duty statuses
- **Map Data**: Returns polylines and markers for frontend map display
- **Trip Validation**: Checks if trips are feasible within HOS rules

## API Endpoints

### POST `/api/eld-trip-planner/`

Main endpoint for trip planning and ELD log generation.

#### Request Body

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Los Angeles, CA",
  "dropoff_location": "Miami, FL",
  "current_cycle_used": 25.5
}
```

#### Response

```json
{
  "status": "success",
  "compliance": {
    "status": "valid|violation",
    "reason": "Explanation if violation"
  },
  "summary": {
    "total_distance_miles": 2015.5,
    "total_duration_hours": 28.3,
    "cycle_remaining": 44.5,
    "days_required": 3
  },
  "map_data": {
    "polyline": "encoded_polyline_string",
    "stops": [],
    "markers": [
      {
        "lat": 41.8781,
        "lng": -87.6298,
        "type": "pickup",
        "label": "Los Angeles, CA"
      }
    ]
  },
  "driver_data": {
    "driverName": "John Smith",
    "date": "2025-01-15",
    "terminal": "Green Bay, WI",
    "carrier": "Schneider National Carriers",
    "vehicle": "T-12345",
    "miles": "1450",
    "coDriver": "",
    "driverSignature": "J.S.",
    "pickupLocation": "Los Angeles, CA",
    "dropoffLocation": "Miami, FL"
  },
  "eld_logs": [
    {
      "day": 1,
      "events": [
        {
          "start": "06:00",
          "end": "06:30",
          "status": "ON",
          "label": "Pickup at Los Angeles, CA"
        }
      ]
    }
  ],
  "duty_events": [
    {
      "start": "06:00",
      "end": "06:30",
      "status": "ON",
      "label": "Pickup at Los Angeles, CA"
    }
  ]
}
```

## HOS Rules Implemented

- **70-hour cycle** in 8 days for property-carrying drivers
- **11 hours maximum driving** per day
- **14 hours maximum duty** per day (driving + fueling + pickup/drop-off)
- **10 consecutive hours off-duty** between shifts
- **30-minute break** required before 8 hours of consecutive driving
- **Pickup/Drop-off**: 0.5 hours each (on-duty, not driving)
- **Fueling**: 0.5 hours, once per duty day if distance > 1000 miles

## Setup Instructions

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Get Google Maps API Key**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Directions API
   - Create API key
   - Replace `YOUR_GOOGLE_MAPS_API_KEY` in `views.py`

3. **Run Django Server**:

   ```bash
   python manage.py runserver
   ```

4. **Test the API**:
   ```bash
   python test_api.py
   ```

## Testing

The `test_api.py` script demonstrates how to use the API:

```bash
cd backend
python test_api.py
```

This will send a sample request and display the full response including:

- Trip summary and compliance status
- Driver information
- Map markers and stops
- Daily ELD logs with duty events

## Frontend Integration

The API returns data in the exact format needed by the frontend ELD log component:

- `duty_events`: Array of events for the ELD log grid
- `driver_data`: Form data for the log header
- `map_data`: Polylines and markers for map display
- `compliance`: HOS compliance status and validation

## Error Handling

The API handles various error conditions:

- **400 Bad Request**: Missing required fields
- **500 Internal Server Error**: Google Maps API failures, server errors
- **Validation Errors**: Invalid input data

## Future Enhancements

- Database persistence for trip history
- User authentication and trip management
- Real-time GPS tracking integration
- Advanced HOS rule variations
- Multi-day trip optimization
