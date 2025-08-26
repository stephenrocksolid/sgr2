# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# Import Celery app only if it's available
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not available, create a dummy app
    class DummyCeleryApp:
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    celery_app = DummyCeleryApp()
    __all__ = ('celery_app',)
