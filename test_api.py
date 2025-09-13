#!/usr/bin/env python3
"""
Test script for the ELD Trip Planner API
Run this to test the API endpoint with sample data
"""

import requests
import json

# API endpoint
API_URL = "http://localhost:8000/api/eld-trip-planner/"

# Sample test data
test_data = {
    "current_location": "Chicago, IL",
    "pickup_location": "Los Angeles, CA", 
    "dropoff_location": "Miami, FL",
    "current_cycle_used": 25.5
}

def test_api():
    """Test the ELD Trip Planner API"""
    print("Testing ELD Trip Planner API...")
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    print("-" * 50)
    
    try:
        response = requests.post(API_URL, json=test_data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("-" * 50)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Trip Status: {data.get('compliance', {}).get('status', 'unknown')}")
            print(f"Total Distance: {data.get('summary', {}).get('total_distance_miles', 'N/A')} miles")
            print(f"Total Duration: {data.get('summary', {}).get('total_duration_hours', 'N/A')} hours")
            print(f"Days Required: {data.get('summary', {}).get('days_required', 'N/A')}")
            print(f"Cycle Remaining: {data.get('summary', {}).get('cycle_remaining', 'N/A')} hours")
            
            print("\n📋 Driver Data:")
            driver_data = data.get('driver_data', {})
            for key, value in driver_data.items():
                print(f"  {key}: {value}")
            
            print("\n🗺️  Map Markers:")
            markers = data.get('map_data', {}).get('markers', [])
            for marker in markers:
                print(f"  {marker['type']}: {marker['label']} ({marker['lat']}, {marker['lng']})")
            
            print("\n📝 Daily Logs:")
            daily_logs = data.get('eld_logs', [])
            for day_log in daily_logs:
                print(f"  Day {day_log['day']}:")
                for event in day_log['events']:
                    print(f"    {event['start']}-{event['end']}: {event['status']} - {event['label']}")
            
        else:
            print("❌ ERROR!")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR!")
        print("Make sure the Django server is running on localhost:8000")
        print("Run: python manage.py runserver")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_api()
