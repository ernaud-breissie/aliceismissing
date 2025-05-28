import logging
from django.template.exceptions import TemplateSyntaxError, TemplateDoesNotExist
from django.http import HttpResponseServerError
import traceback

logger = logging.getLogger(__name__)

class TemplateErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, (TemplateSyntaxError, TemplateDoesNotExist)):
            error_details = f"Template Error on {request.path}:\n"
            error_details += f"Error Type: {type(exception).__name__}\n"
            error_details += f"Message: {str(exception)}\n"
            
            if hasattr(exception, 'exc_info') and exception.exc_info:
                exc_type, exc_value, exc_traceback = exception.exc_info
                error_details += f"Line: {getattr(exception, 'lineno', 'N/A')}\n"
                error_details += f"Source: {getattr(exception, 'source', ('N/A', (0,0)))[0]}\n"
            elif hasattr(exception, 'template_debug'):
                error_details += f"Line: {exception.template_debug.get('line', 'N/A')}\n"
                error_details += f"During: {exception.template_debug.get('during', 'N/A')}\n"

            logger.error(error_details, exc_info=True)
            
        return None 