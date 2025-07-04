from django.urls import path
from . import views

app_name = 'qa_agent'

urlpatterns = [
    # Main chat interface
    path('', views.chat_interface, name='chat'),
    path('chat/', views.chat_interface, name='chat_interface'),
    
    # Conversation management
    path('history/', views.conversation_history, name='conversation_history'),
    path('conversation/<str:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    
    # API endpoints
    path('api/feedback/', views.api_submit_feedback, name='api_submit_feedback'),
    path('api/status/', views.api_agent_status, name='api_agent_status'),
    
    # Analytics and admin
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('demo/', views.demo_conversation, name='demo_conversation'),
] 