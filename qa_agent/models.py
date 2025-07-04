from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Conversation(models.Model):
    """
    Model to track chat conversations with the Claude QA Agent
    """
    conversation_id = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['conversation_id']),
            models.Index(fields=['user', '-updated_at']),
        ]
    
    def __str__(self):
        title = self.title or f"Conversation {self.conversation_id[:8]}..."
        return f"{title} ({self.user.username if self.user else 'Anonymous'})"
    
    def generate_title(self):
        """Generate a title based on the first user message"""
        first_message = self.messages.filter(sender='user').first()
        if first_message:
            content = first_message.content[:50]
            self.title = content + "..." if len(first_message.content) > 50 else content
            self.save(update_fields=['title'])
    
    @property
    def message_count(self):
        return self.messages.count()
    
    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """
    Model to store individual messages in conversations
    """
    SENDER_CHOICES = [
        ('user', 'User'),
        ('assistant', 'AI Assistant'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    # Metadata fields
    tools_used = models.JSONField(default=list, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    processing_time = models.FloatField(null=True, blank=True)  # in seconds
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
    
    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.get_sender_display()}: {content_preview}"


class ToolExecution(models.Model):
    """
    Model to track individual tool executions for analytics and debugging
    """
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
    ]
    
    message = models.ForeignKey(Message, related_name='tool_executions', on_delete=models.CASCADE)
    tool_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Tool-specific data
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['started_at']
        indexes = [
            models.Index(fields=['message', 'started_at']),
            models.Index(fields=['tool_name', 'status']),
        ]
    
    def __str__(self):
        return f"{self.tool_name} ({self.status}) - {self.started_at}"
    
    @property
    def execution_time(self):
        """Calculate execution time in seconds"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def mark_completed(self, output_data=None):
        """Mark tool execution as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if output_data:
            self.output_data = output_data
        self.save(update_fields=['status', 'completed_at', 'output_data'])
    
    def mark_error(self, error_message):
        """Mark tool execution as failed"""
        self.status = 'error'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])


class UserFeedback(models.Model):
    """
    Model to collect user feedback on AI responses
    """
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]
    
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['rating', 'created_at']),
        ]
    
    def __str__(self):
        return f"Rating {self.rating}/5 for message {self.message.id}"


class AgentMetrics(models.Model):
    """
    Model to track agent performance metrics
    """
    date = models.DateField(default=timezone.now)
    total_conversations = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)
    successful_tool_executions = models.IntegerField(default=0)
    failed_tool_executions = models.IntegerField(default=0)
    average_user_rating = models.FloatField(null=True, blank=True)
    
    class Meta:
        unique_together = ['date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Metrics for {self.date}" 