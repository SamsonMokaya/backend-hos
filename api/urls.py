from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('eld-trip-planner/', views.eld_trip_planner, name='eld_trip_planner'),
]
