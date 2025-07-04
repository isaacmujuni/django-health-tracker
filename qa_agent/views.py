from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Conversation, Message, ToolExecution, UserFeedback, AgentMetrics
from .claude_agent import ClaudeQAAgent
import json
import asyncio


def chat_interface(request):
    """
    Main chat interface view
    """
    if request.user.is_authenticated:
        # Get user's recent conversations
        recent_conversations = Conversation.objects.filter(
            user=request.user
        ).order_by('-updated_at')[:5]
    else:
        recent_conversations = []
    
    context = {
        'recent_conversations': recent_conversations,
        'user_authenticated': request.user.is_authenticated,
    }
    
    return render(request, 'qa_agent/chat.html', context)


@login_required
def conversation_history(request):
    """
    View to display user's conversation history
    """
    conversations = Conversation.objects.filter(
        user=request.user
    ).annotate(
        message_count=Count('messages')
    ).order_by('-updated_at')
    
    # Pagination
    paginator = Paginator(conversations, 20)
    page_number = request.GET.get('page')
    page_conversations = paginator.get_page(page_number)
    
    context = {
        'conversations': page_conversations,
        'total_conversations': conversations.count(),
    }
    
    return render(request, 'qa_agent/conversation_history.html', context)


@login_required
def conversation_detail(request, conversation_id):
    """
    View to display a specific conversation
    """
    conversation = get_object_or_404(
        Conversation, 
        conversation_id=conversation_id, 
        user=request.user
    )
    
    messages = conversation.messages.all().order_by('created_at')
    
    context = {
        'conversation': conversation,
        'messages': messages,
    }
    
    return render(request, 'qa_agent/conversation_detail.html', context)


@csrf_exempt
def api_submit_feedback(request):
    """
    API endpoint to submit user feedback on AI responses
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        if not message_id or not rating:
            return JsonResponse({'error': 'message_id and rating required'}, status=400)
        
        if rating not in [1, 2, 3, 4, 5]:
            return JsonResponse({'error': 'rating must be 1-5'}, status=400)
        
        message = get_object_or_404(Message, id=message_id, sender='assistant')
        
        # Check if user owns this conversation (if authenticated)
        if request.user.is_authenticated and message.conversation.user != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Create or update feedback
        feedback, created = UserFeedback.objects.update_or_create(
            message=message,
            defaults={
                'rating': rating,
                'comment': comment,
            }
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'feedback_id': feedback.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def analytics_dashboard(request):
    """
    Dashboard view for QA agent analytics (admin only)
    """
    if not request.user.is_staff:
        return redirect('qa_agent:chat')
    
    # Get recent metrics
    recent_metrics = AgentMetrics.objects.order_by('-date')[:30]
    
    # Calculate summary statistics
    total_conversations = Conversation.objects.count()
    total_messages = Message.objects.count()
    total_tool_executions = ToolExecution.objects.count()
    
    # Tool usage statistics
    tool_usage = ToolExecution.objects.values('tool_name').annotate(
        count=Count('id'),
        success_rate=Count('id', filter=Q(status='completed')) * 100.0 / Count('id')
    ).order_by('-count')
    
    # Recent feedback
    recent_feedback = UserFeedback.objects.select_related('message').order_by('-created_at')[:10]
    
    # Average ratings
    avg_rating = UserFeedback.objects.aggregate(
        avg=Avg('rating')
    )['avg'] or 0
    
    context = {
        'recent_metrics': recent_metrics,
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'total_tool_executions': total_tool_executions,
        'tool_usage': tool_usage,
        'recent_feedback': recent_feedback,
        'average_rating': round(avg_rating, 2),
    }
    
    return render(request, 'qa_agent/analytics_dashboard.html', context)


def api_agent_status(request):
    """
    API endpoint to check agent status and health
    """
    try:
        # Basic health check
        agent = ClaudeQAAgent()
        
        # Check recent activity
        recent_conversations = Conversation.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        recent_errors = ToolExecution.objects.filter(
            status='error',
            started_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        status = {
            'status': 'healthy',
            'recent_conversations_24h': recent_conversations,
            'recent_errors_24h': recent_errors,
            'available_tools': len(agent.tools),
            'timestamp': timezone.now().isoformat(),
        }
        
        return JsonResponse(status)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        }, status=500)


# Helper function for demo/testing
async def demo_conversation(request):
    """
    Demo view to test the Claude agent functionality
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access only'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', 'What are some good exercises for weight loss?')
            
            agent = ClaudeQAAgent()
            
            # Mock user context
            user_context = {
                'user_id': request.user.id,
                'recent_activities': [
                    {'type': 'RUN', 'duration': '30:00', 'date': '2024-01-01'}
                ],
                'goals': [{'type': 'Weight Loss', 'target': 75}]
            }
            
            response = await agent.process_question(question, user_context)
            
            return JsonResponse({
                'success': True,
                'response': response
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return render(request, 'qa_agent/demo.html') 