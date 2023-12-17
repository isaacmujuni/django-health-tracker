from django.urls import path
from . import views

urlpatterns = [
    path('activities/', views.activity_list, name='activity_list'),
    path('diet/', views.diet_log, name='diet_log'),
    # Add more URL patterns as needed
]
