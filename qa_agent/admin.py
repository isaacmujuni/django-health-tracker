from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from .models import Conversation, Message, ToolExecution, UserFeedback, AgentMetrics


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['conversation_id', 'user', 'title', 'message_count', 'created_at', 'updated_at']
    list_filter = ['created_at', 'is_active']
    search_fields = ['conversation_id', 'user__username', 'title']
    readonly_fields = ['conversation_id', 'created_at', 'updated_at', 'message_count']
    date_hierarchy = 'created_at'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user').annotate(
            msg_count=Count('messages')
        )


class ToolExecutionInline(admin.TabularInline):
    model = ToolExecution
    extra = 0
    readonly_fields = ['tool_name', 'status', 'started_at', 'completed_at', 'execution_time']
    fields = ['tool_name', 'status', 'started_at', 'completed_at', 'execution_time']
    
    def execution_time(self, obj):
        if obj.completed_at:
            return f"{obj.execution_time:.2f}s"
        return "Running..."
    execution_time.short_description = 'Duration'


class UserFeedbackInline(admin.StackedInline):
    model = UserFeedback
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_link', 'sender', 'content_preview', 'tools_used_display', 'created_at']
    list_filter = ['sender', 'created_at', 'tools_used']
    search_fields = ['content', 'conversation__conversation_id']
    readonly_fields = ['created_at', 'tools_used', 'confidence_score', 'processing_time']
    inlines = [ToolExecutionInline, UserFeedbackInline]
    date_hierarchy = 'created_at'
    
    def conversation_link(self, obj):
        url = reverse('admin:qa_agent_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{}</a>', url, obj.conversation.conversation_id[:12])
    conversation_link.short_description = 'Conversation'
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'
    
    def tools_used_display(self, obj):
        if obj.tools_used:
            return ", ".join(obj.tools_used)
        return "None"
    tools_used_display.short_description = 'Tools Used'


@admin.register(ToolExecution)
class ToolExecutionAdmin(admin.ModelAdmin):
    list_display = ['id', 'tool_name', 'status', 'message_link', 'execution_time_display', 'started_at']
    list_filter = ['tool_name', 'status', 'started_at']
    search_fields = ['tool_name', 'message__content']
    readonly_fields = ['started_at', 'completed_at', 'execution_time_display']
    date_hierarchy = 'started_at'
    
    def message_link(self, obj):
        url = reverse('admin:qa_agent_message_change', args=[obj.message.id])
        return format_html('<a href="{}">Message {}</a>', url, obj.message.id)
    message_link.short_description = 'Message'
    
    def execution_time_display(self, obj):
        if obj.execution_time:
            return f"{obj.execution_time:.2f}s"
        elif obj.status == 'started':
            return "Running..."
        return "N/A"
    execution_time_display.short_description = 'Duration'


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'message_link', 'rating', 'rating_stars', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['comment', 'message__content']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def message_link(self, obj):
        url = reverse('admin:qa_agent_message_change', args=[obj.message.id])
        return format_html('<a href="{}">Message {}</a>', url, obj.message.id)
    message_link.short_description = 'Message'
    
    def rating_stars(self, obj):
        stars = "⭐" * obj.rating + "☆" * (5 - obj.rating)
        return format_html('<span style="font-size: 16px;">{}</span>', stars)
    rating_stars.short_description = 'Rating'


@admin.register(AgentMetrics)
class AgentMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_conversations', 'total_messages', 
        'average_response_time', 'tool_success_rate', 'average_user_rating'
    ]
    list_filter = ['date']
    readonly_fields = ['date']
    date_hierarchy = 'date'
    
    def tool_success_rate(self, obj):
        total = obj.successful_tool_executions + obj.failed_tool_executions
        if total > 0:
            rate = (obj.successful_tool_executions / total) * 100
            return f"{rate:.1f}%"
        return "N/A"
    tool_success_rate.short_description = 'Tool Success Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-date')


# Customize admin site header
admin.site.site_header = "Health Tracker Claude QA Agent Admin"
admin.site.site_title = "QA Agent Admin"
admin.site.index_title = "Claude QA Agent Administration" 