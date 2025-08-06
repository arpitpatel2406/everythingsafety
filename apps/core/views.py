from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import render


@require_http_methods(["GET"])
@csrf_exempt
def health_check(request):
    """
    Health check endpoint for monitoring
    """
    health_data = {
        'status': 'healthy',
        'timestamp': request.META.get('HTTP_DATE'),
        'services': {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_data['services']['database'] = 'healthy'
    except Exception as e:
        health_data['services']['database'] = f'unhealthy: {str(e)}'
        health_data['status'] = 'unhealthy'

    return JsonResponse(health_data)


@require_http_methods(["GET"])
@csrf_exempt
def ready_check(request):
    """
    Readiness check endpoint
    """
    return JsonResponse({'status': 'ready'})


@require_http_methods(["GET"])
@csrf_exempt
def dashboard(request):
    """
    Dashboard view endpoint
    """
    # Placeholder for dashboard logic
    return render(request, 'dashboard.html', {})