from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
from django.conf import settings
import json
from datetime import datetime, timedelta
import math

@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def eld_trip_planner(request):
    """
    ELD Trip Planner API endpoint
    
    Inputs:
    - current_location: string (e.g., "Chicago, IL")
    - pickup_location: string (e.g., "Los Angeles, CA")
    - dropoff_location: string (e.g., "Miami, FL")
    - current_cycle_used: float (hours already used in 70h cycle)
    
    Outputs:
    - Map data (polyline, stops, markers)
    - Daily ELD logs with proper HOS compliance
    - Driver info and form data
    - Trip summary and compliance status
    """
    
    try:
        # Extract input data
        data = request.data
        pickup_location = data.get('pickup_location', '')
        dropoff_location = data.get('dropoff_location', '')
        current_cycle_used = float(data.get('current_cycle_used', 0))
        
        # Validate inputs
        if not all([pickup_location, dropoff_location]):
            return Response({
                'error': 'Missing required fields: pickup_location, dropoff_location'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Google Maps API configuration
        GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY
        directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        
        # Get route data from Google Maps
        route_data = get_route_data(
            directions_url, 
            GOOGLE_MAPS_API_KEY,
            pickup_location, 
            dropoff_location
        )
        
        if not route_data:
            print("Failed to get route data from Google Maps")
            return Response({
                'error': 'Failed to get route data from Google Maps'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Extract route information
        total_distance = route_data['total_distance_miles']
        total_duration = route_data['total_duration_hours']
        polyline = route_data['polyline']
        route_steps = route_data['steps']
        
        # Generate ELD logs with HOS compliance
        eld_data = generate_eld_logs(
            total_distance, 
            total_duration, 
            current_cycle_used,
            pickup_location,
            dropoff_location
        )
        
        # Generate driver info and form data
        driver_data = generate_driver_data(pickup_location, dropoff_location)
        
        # Generate stops and markers for map
        stops_data = generate_stops_data(route_steps, pickup_location, dropoff_location, route_data)
        
        # Check compliance
        compliance_status = check_compliance(eld_data, current_cycle_used, total_duration)
        
        
        # If violation, return only violation data
        if compliance_status['status'] == 'violation':
            response_data = {
                'status': 'violation',
                'compliance': compliance_status,
                'summary': {
                    'total_distance_miles': total_distance,
                    'total_duration_hours': total_duration,
                    'cycle_remaining': 70 - current_cycle_used,
                    'days_required': eld_data['days_required']
                },
                'violation': {
                    'message': f"Trip requires {compliance_status['total_on_duty_hours']:.1f} hours but only {70 - current_cycle_used:.1f} hours remaining in cycle",
                    'required_hours': compliance_status['total_on_duty_hours'],
                    'available_hours': 70 - current_cycle_used,
                    'shortfall_hours': compliance_status['total_on_duty_hours'] - (70 - current_cycle_used)
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        # Prepare full response for valid trips
        response_data = {
        'status': 'success',
            'compliance': compliance_status,
            'summary': {
                'total_distance_miles': total_distance,
                'total_duration_hours': total_duration,
                'cycle_remaining': 70 - current_cycle_used,
                'days_required': eld_data['days_required']
            },
            'map_data': {
                'polyline': polyline,
                'stops': stops_data['stops'],
                'markers': stops_data['markers']
            },
            'driver_data': driver_data,
            'eld_logs': eld_data['daily_logs'],
            'duty_events': eld_data['duty_events']
        }

        print(response_data)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_route_data(api_url, api_key, pickup_loc, dropoff_loc):
    """Get route data from Google Maps Directions API"""
    try:
        # Direct route from pickup to dropoff
        params = {
            'origin': pickup_loc,
            'destination': dropoff_loc,
            'key': api_key,
            'units': 'imperial'
        }
        
        response = requests.get(api_url, params=params)
        data = response.json()
        
        if data['status'] != 'OK':
            return None
        
        # Extract route data
        total_distance = 0
        total_duration = 0
        all_steps = []
        
        for leg in data['routes'][0]['legs']:
            total_distance += leg['distance']['value'] / 1609.34  # Convert meters to miles
            total_duration += leg['duration']['value'] / 3600    # Convert seconds to hours
            all_steps.extend(leg['steps'])
        
        return {
            'total_distance_miles': round(total_distance, 2),
            'total_duration_hours': round(total_duration, 2),
            'polyline': data['routes'][0]['overview_polyline']['points'],
            'steps': all_steps,
            'legs': data['routes'][0]['legs']
        }
        
    except Exception as e:
        print(f"Error getting route data: {e}")
        return None


def generate_eld_logs(total_distance, total_duration, cycle_used, pickup_loc, dropoff_loc):
    """Generate ELD logs with proper HOS compliance and continuous timeline"""
    
    # HOS Rules
    MAX_DRIVING_PER_DAY = 11
    BREAK_REQUIRED_AFTER = 7.5  # hours of driving
    BREAK_DURATION = 0.5
    FUEL_DURATION = 0.5
    PICKUP_DURATION = 0.5
    DROPOFF_DURATION = 0.5
    REST_DURATION = 10
    
    # Calculate if refueling needed
    needs_refueling = total_distance > 1000
    
    # Generate daily logs with continuous timeline
    daily_logs = []
    duty_events = []
    
    # Start at 6:00 AM on the first day
    current_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
    
    # Calculate how many days we need
    days_needed = max(1, int((total_duration + 12) / 24))  # +12 for rest periods
    
    # Distribute driving time across days
    remaining_driving = total_duration
    day = 1
    
    # Generate each day with proper continuous timeline
    while remaining_driving > 0 and day <= days_needed:
        day_events = []
        day_start_time = current_time
        
        # Pre-trip inspection (only on first day)
        if day == 1:
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': (current_time + timedelta(hours=0.5)).strftime("%H:%M"),
                'status': 'ON',
                'label': f'Pre-trip inspection & Pickup at {pickup_loc}'
            })
            current_time += timedelta(hours=0.5)
        else:
            # Pre-trip inspection for subsequent days
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': (current_time + timedelta(hours=0.5)).strftime("%H:%M"),
                'status': 'ON',
                'label': 'Pre-trip inspection'
            })
            current_time += timedelta(hours=0.5)
        
        # Calculate driving time for this day (max 11 hours)
        day_driving = min(MAX_DRIVING_PER_DAY, remaining_driving)
        
        # Morning driving session
        morning_drive = min(7.5, day_driving)
        if morning_drive > 0:
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': (current_time + timedelta(hours=morning_drive)).strftime("%H:%M"),
                'status': 'DRIVING',
                'label': 'Drive' if day == 1 else 'Continue driving'
            })
            current_time += timedelta(hours=morning_drive)
            remaining_driving -= morning_drive
        
        # Break if drove 7.5+ hours
        if morning_drive >= BREAK_REQUIRED_AFTER:
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': (current_time + timedelta(hours=BREAK_DURATION)).strftime("%H:%M"),
                'status': 'OFF',
                'label': 'Break'
            })
            current_time += timedelta(hours=BREAK_DURATION)
        
        # Afternoon driving session (remaining time for this day)
        afternoon_drive = min(day_driving - morning_drive, remaining_driving)
        if afternoon_drive > 0:
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': (current_time + timedelta(hours=afternoon_drive)).strftime("%H:%M"),
                'status': 'DRIVING',
                'label': 'Continue driving'
            })
            current_time += timedelta(hours=afternoon_drive)
            remaining_driving -= afternoon_drive
        
        # Fuel if needed (only on day 2+)
        if needs_refueling and day > 1:
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': (current_time + timedelta(hours=FUEL_DURATION)).strftime("%H:%M"),
                'status': 'ON',
                'label': 'Fueling'
            })
            current_time += timedelta(hours=FUEL_DURATION)
        
        # Dropoff on last day
        if remaining_driving <= 0:
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': (current_time + timedelta(hours=DROPOFF_DURATION)).strftime("%H:%M"),
                'status': 'ON',
                'label': f'Dropoff at {dropoff_loc}'
            })
            current_time += timedelta(hours=DROPOFF_DURATION)
            
            # Fill remaining time with OFF duty to complete 24 hours
            day_end_time = day_start_time + timedelta(hours=24)
            remaining_time = (day_end_time - current_time).total_seconds() / 3600  # hours
            
            if remaining_time > 0:
                day_events.append({
                    'start': current_time.strftime("%H:%M"),
                    'end': day_end_time.strftime("%H:%M"),
                    'status': 'OFF',
                    'label': 'Off duty - end of day'
                })
                current_time = day_end_time
        else:
            # Sleep for the night - calculate to end at 6:00 AM next day
            next_day_start = current_time.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
            sleep_duration = (next_day_start - current_time).total_seconds() / 3600  # hours
            
            day_events.append({
                'start': current_time.strftime("%H:%M"),
                'end': next_day_start.strftime("%H:%M"),
                'status': 'SB',
                'label': 'Sleep'
            })
            
            # Move to next day at 6:00 AM
            current_time = next_day_start
        
        # Add day to logs
        daily_logs.append({
            'day': day,
            'events': day_events
        })
        
        day += 1
    
    # Add all events to duty_events
    for day_log in daily_logs:
        duty_events.extend(day_log['events'])
    
    return {
        'daily_logs': daily_logs,
        'duty_events': duty_events,
        'days_required': len(daily_logs)
    }


def generate_driver_data(pickup_loc, dropoff_loc):
    """Generate driver info and form data"""
    return {
        'driverName': 'John Smith',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'terminal': 'Green Bay, WI',
        'carrier': 'Schneider National Carriers',
        'vehicle': 'T-12345',
        'miles': str(int(1000 + (hash(pickup_loc + dropoff_loc) % 500))),  # Generate realistic miles
        'coDriver': '',
        'driverSignature': 'J.S.',
        'pickupLocation': pickup_loc,
        'dropoffLocation': dropoff_loc
    }


def generate_stops_data(route_steps, pickup_loc, dropoff_loc, route_data=None):
    """Generate stops and markers for map display using real coordinates"""
    stops = []
    markers = []
    
    # Extract real coordinates from Google Maps response
    if route_data and 'legs' in route_data:
        # Get pickup coordinates (start of first leg)
        pickup_coords = route_data['legs'][0]['start_location']
        markers.append({
            'lat': pickup_coords['lat'],
            'lng': pickup_coords['lng'],
            'type': 'pickup',
            'label': pickup_loc
        })
        
        # Get dropoff coordinates (end of last leg)
        dropoff_coords = route_data['legs'][-1]['end_location']
        markers.append({
            'lat': dropoff_coords['lat'],
            'lng': dropoff_coords['lng'],
            'type': 'dropoff',
            'label': dropoff_loc
        })
        
        # Calculate fuel stop location (middle of route)
        if len(route_steps) > 10:  # Long trip needs fuel
            mid_point = len(route_steps) // 2
            fuel_coords = route_steps[mid_point]['end_location']
            markers.append({
                'lat': fuel_coords['lat'],
                'lng': fuel_coords['lng'],
                'type': 'fuel',
                'label': 'Fuel Stop'
            })
        
        # Calculate rest stop location (1/3 through route)
        rest_point = len(route_steps) // 3
        rest_coords = route_steps[rest_point]['end_location']
        markers.append({
            'lat': rest_coords['lat'],
            'lng': rest_coords['lng'],
            'type': 'rest',
            'label': 'Rest Stop'
        })
        
    else:
        # Fallback to hardcoded coordinates if no route data
        markers.append({
            'lat': 41.8781,
            'lng': -87.6298,
            'type': 'pickup',
            'label': pickup_loc
        })
        markers.append({
            'lat': 34.0522,
            'lng': -118.2437,
            'type': 'dropoff',
            'label': dropoff_loc
        })
    
    return {
        'stops': stops,
        'markers': markers
    }


def check_compliance(eld_data, cycle_used, total_driving_hours):
    """Check HOS compliance"""
    # Calculate total on-duty time from Google Maps data
    # Add pickup (0.5h) + driving time + dropoff (0.5h) + fueling if needed
    pickup_time = 0.5
    dropoff_time = 0.5
    fueling_time = 0.5 if total_driving_hours > 11 else 0  # Fuel if more than 1 day of driving
    
    total_on_duty = pickup_time + total_driving_hours + dropoff_time + fueling_time
    
    cycle_remaining = 70 - cycle_used
    
    if total_on_duty > cycle_remaining:
        return {
            'status': 'violation',
            'total_on_duty_hours': total_on_duty,
            'cycle_remaining': cycle_remaining,
            'reason': f'Total on-duty time ({total_on_duty:.1f}h) exceeds cycle remaining ({cycle_remaining:.1f}h)'
        }
    else:
        return {
            'status': 'valid',
            'total_on_duty_hours': total_on_duty,
            'cycle_remaining': cycle_remaining - total_on_duty
        }