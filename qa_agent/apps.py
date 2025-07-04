from django.apps import AppConfig


class QaAgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qa_agent'
    verbose_name = 'Claude QA Agent'
    
    def ready(self):
        """
        Initialize the QA agent when Django starts
        """
        pass 