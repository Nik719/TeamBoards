from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """
        Import signals here so they are connected when Django starts.
        This is the canonical pattern — importing in models.py or views.py
        risks double-registration or import-order issues.
        """
        import api.signals  # noqa: F401
