import uuid
import json
import logging
from django.utils import timezone

logger = logging.getLogger('actividades')

class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generar o conservar el correlation_id
        correlation_id = request.headers.get('X-Correlation-ID')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        request.correlation_id = correlation_id

        # Log request_received
        logger.info(json.dumps({
            "timestamp": timezone.now().isoformat(),
            "level": "info",
            "event": "request_received",
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.path,
        }))

        response = self.get_response(request)

        # Log request_completed
        logger.info(json.dumps({
            "timestamp": timezone.now().isoformat(),
            "level": "info",
            "event": "request_completed",
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.path,
            "result": response.status_code
        }))

        # Retornar el header
        response['X-Correlation-ID'] = correlation_id
        return response
