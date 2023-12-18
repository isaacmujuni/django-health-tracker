from django.urls import path
from django.contrib.auth.views import LoginView
from .views import add_activity, add_diet_log, custom_logout, profile
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('activities/', views.activity_list, name='activity_list'),
    path('diet/', views.diet_log, name='diet_log'),
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='fitness/login.html'), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('activities/add/', add_activity, name='add_activity'),
    path('diet/add/', add_diet_log, name='add_diet_log'),
    path('weight/', views.weight_tracker, name='weight_tracker'),
    path('profile/', profile, name='profile'),]
