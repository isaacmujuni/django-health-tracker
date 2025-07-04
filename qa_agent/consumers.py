import json
import asyncio
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .claude_agent import ClaudeQAAgent
from .models import Conversation, Message


class QAAgentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time Claude QA Agent communication
    Handles tool execution updates and streaming responses
    """
    
    async def connect(self):
        self.room_name = f"qa_agent_{self.scope['user'].id if self.scope['user'].is_authenticated else 'anonymous'}"
        self.room_group_name = f'qa_agent_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Initialize Claude agent with status callback
        self.claude_agent = ClaudeQAAgent()
        self.claude_agent.set_status_callback(self.send_status_update)
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to AI Assistant'
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'user_message':
                await self.handle_user_message(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
                
        except Exception as e:
            await self.send_status_update('error', 'system', f"Error processing message: {str(e)}")
    
    async def handle_user_message(self, data):
        """Handle incoming user message and process with Claude agent"""
        user_message = data.get('message', '')
        conversation_id = data.get('conversation_id')
        
        if not user_message.strip():
            return
        
        # Get or create conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            await self.send(text_data=json.dumps({
                'type': 'conversation_id',
                'conversation_id': conversation_id
            }))
        
        # Save user message
        await self.save_message(conversation_id, 'user', user_message)
        
        # Send thinking indicator
        await self.send_status_update('thinking_started', 'system', 'AI is analyzing your question...')
        
        try:
            # Process with Claude agent
            user_context = await self.get_user_context()
            response = await self.claude_agent.process_question(user_message, user_context)
            
            # Send final response
            await self.send_status_update('thinking_stopped', 'system', '')
            await self.send(text_data=json.dumps({
                'type': 'assistant_response',
                'message': response['answer'],
                'tools_used': response.get('tools_used', []),
                'confidence': response.get('confidence', 0.8)
            }))
            
            # Save assistant response
            await self.save_message(conversation_id, 'assistant', response['answer'])
            
        except Exception as e:
            await self.send_status_update('thinking_stopped', 'system', '')
            await self.send_status_update('error', 'system', f"Sorry, I encountered an error: {str(e)}")
    
    async def send_status_update(self, status_type, tool_name, message):
        """Send status updates to frontend for real-time tool operation display"""
        await self.send(text_data=json.dumps({
            'type': status_type,
            'tool_name': tool_name,
            'message': message,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    @database_sync_to_async
    def get_user_context(self):
        """Get user context for personalized responses"""
        if not self.scope['user'].is_authenticated:
            return {}
        
        user = self.scope['user']
        
        # Import here to avoid circular imports
        from fitness.models import FitnessActivity, DietaryLog, WeightEntry, FitnessGoal
        
        try:
            recent_activities = FitnessActivity.objects.filter(user=user).order_by('-date_time')[:5]
            recent_diet = DietaryLog.objects.filter(user=user).order_by('-date_time')[:3]
            latest_weight = WeightEntry.objects.filter(user=user).order_by('-date').first()
            goals = FitnessGoal.objects.filter(user=user)
            
            return {
                'user_id': user.id,
                'username': user.username,
                'activity_count': recent_activities.count(),
                'recent_activities': [
                    {
                        'type': activity.activity_type,
                        'duration': str(activity.duration),
                        'date': activity.date_time.isoformat()
                    } for activity in recent_activities
                ],
                'recent_diet': [
                    {
                        'food': diet.food_item,
                        'calories': diet.calories,
                        'date': diet.date_time.isoformat()
                    } for diet in recent_diet
                ],
                'latest_weight': latest_weight.weight if latest_weight else None,
                'goals': [
                    {
                        'type': goal.goal_type,
                        'target': goal.target_value,
                        'progress': goal.current_progress
                    } for goal in goals
                ]
            }
        except Exception as e:
            return {'user_id': user.id, 'error': str(e)}
    
    @database_sync_to_async
    def save_message(self, conversation_id, sender, content):
        """Save message to database"""
        try:
            conversation, created = Conversation.objects.get_or_create(
                conversation_id=conversation_id,
                defaults={
                    'user': self.scope['user'] if self.scope['user'].is_authenticated else None
                }
            )
            
            Message.objects.create(
                conversation=conversation,
                sender=sender,
                content=content
            )
        except Exception as e:
            print(f"Error saving message: {e}")


class ProgressTrackingMixin:
    """
    Mixin to add progress tracking to Claude agent operations
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_callback = None
    
    def set_status_callback(self, callback):
        """Set callback function for status updates"""
        self.status_callback = callback
    
    async def notify_tool_started(self, tool_name, description):
        """Notify that a tool has started execution"""
        if self.status_callback:
            await self.status_callback('tool_started', tool_name, description)
    
    async def notify_tool_completed(self, tool_name, result):
        """Notify that a tool has completed execution"""
        if self.status_callback:
            await self.status_callback('tool_completed', tool_name, result)
    
    async def notify_tool_error(self, tool_name, error):
        """Notify that a tool encountered an error"""
        if self.status_callback:
            await self.status_callback('tool_error', tool_name, str(error))
    
    async def notify_thinking(self, message):
        """Notify about reasoning/thinking process"""
        if self.status_callback:
            await self.status_callback('thinking_update', 'reasoning', message) 