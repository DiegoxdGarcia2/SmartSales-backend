from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        """Conecta las señales cuando la app está lista"""
        import notifications.signals  # noqa
