from django.http import JsonResponse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os, json, uuid
from pathlib import Path
from urllib.parse import parse_qs
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings

from .api import (
    SalesReportProcessor, 
    create_lightspeed_request
)
from .middleware.lightspeed_shopify import ensure_many
"""
2025-08-11 -> $ 4500 mismatch
2025-07-18 -> $ 400  mismatch
"""

def get_sales(request=None):
    """
    Main sales report endpoint with professional structure.
    Now uses SalesReportProcessor for clean, maintainable code.
    """
    try:
        # Initialize the processor
        processor = SalesReportProcessor(timezone="America/New_York")
        
        # Example usage - easy to switch between periods
        # Uncomment the report type you want:
        
        # Daily Report
        report_data = processor.generate_report("daily", date="2025-07-18")
        with open("report.json", "w") as f:
            json.dump(report_data, f)
        # Weekly Report
        # report_data = processor.generate_report("weekly", start_date="2025-07-14")
        
        # Monthly Report (current example)
        # report_data = processor.generate_report("monthly", year=2025, month=7)
        
        # Check for errors
        if "error" in report_data:
            return JsonResponse(
                {"error": report_data["error"]}, 
                status=report_data.get("status_code", 500)
            )
        
        # Return the same exact JsonResponse format as before
        return JsonResponse(report_data)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

def get_daily_sales(request=None):
    """Dedicated function for daily sales reports."""
    processor = SalesReportProcessor()
    
    # Extract date from request if available
    date = None
    if request and request.GET:
        date = request.GET.get('date')
    
    report_data = processor.generate_report("daily", date=date)
    
    if "error" in report_data:
        return JsonResponse(
            {"error": report_data["error"]}, 
            status=report_data.get("status_code", 500)
        )
    
    return JsonResponse(report_data)

def get_weekly_sales(request=None):
    """Dedicated function for weekly sales reports."""
    processor = SalesReportProcessor()
    
    # Extract start_date from request if available
    start_date = None
    if request and request.GET:
        start_date = request.GET.get('start_date')
    
    report_data = processor.generate_report("weekly", start_date=start_date)
    
    if "error" in report_data:
        return JsonResponse(
            {"error": report_data["error"]}, 
            status=report_data.get("status_code", 500)
        )
    
    return JsonResponse(report_data)

def get_monthly_sales(request=None):
    """Dedicated function for monthly sales reports."""
    processor = SalesReportProcessor()
    
    # Extract year/month from request if available
    year = None
    month = None
    if request and request.GET:
        year = request.GET.get('year')
        month = request.GET.get('month')
        # Convert to int if provided
        if year:
            year = int(year)
        if month:
            month = int(month)
    
    report_data = processor.generate_report("monthly", year=year, month=month)
    
    if "error" in report_data:
        return JsonResponse(
            {"error": report_data["error"]}, 
            status=report_data.get("status_code", 500)
        )
    
    return JsonResponse(report_data)

@csrf_exempt
@require_POST
def ls_webhook(request, topic: str):
    """
    DEV MODE: no signature verification.
    Logs headers, raw body, and parsed payload to a file + stdout.
    """
    alias = {
        "inventory": "inventory.update",
        "product":   "product.update",
        "customer":  "customer.update",
        "sale":      "sale.update",
    }
    topic = alias.get(topic, topic)
    raw = request.body  # exact bytes
    content_type = request.META.get("CONTENT_TYPE", "")
    
    # capture headers (hide Authorization just in case)
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() != "authorization"
    }

    # try to parse Lightspeed's typical body: application/x-www-form-urlencoded with 'payload' JSON
    parsed = None
    body_text = raw.decode("utf-8", errors="replace")
    # print(f"Webhook received: {topic} {body_text}")
    if "application/x-www-form-urlencoded" in content_type.lower():
        form = parse_qs(body_text, keep_blank_values=True)
        payload_json = form.get("payload", ["{}"])[0]
        try:
            parsed = json.loads(payload_json)
        except json.JSONDecodeError:
            parsed = {"_payload_raw": payload_json}
    elif "application/json" in content_type.lower():
        try:
            parsed = json.loads(body_text)
        except json.JSONDecodeError:
            parsed = {"_raw_json": body_text}

    event = {
        "topic": topic,
        "received_at": timezone.now().isoformat(),
        "remote_addr": request.META.get("REMOTE_ADDR"),
        "headers": headers,
        "content_type": content_type,
        "raw_body": body_text,
        "parsed": parsed,
    }

    # dump to a local folder for easy replay
    dump_dir = Path(getattr(settings, "WEBHOOK_DUMPS_DIR", settings.BASE_DIR / "webhook_dumps"))
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_file = dump_dir / f"{timezone.now().strftime('%Y%m%d-%H%M%S')}-{topic}-{uuid.uuid4().hex[:8]}.json"
    dump_file.write_text(json.dumps(event, indent=2), encoding="utf-8")

    # also print to console for quick inspection
    print(json.dumps(event, indent=2))

    # IMPORTANT: ACK fast to avoid retries
    return HttpResponse(status=200)

def ensure_webhooks_view(request):
    base = "https://c3b2a3113ca0.ngrok-free.app"
    desired = {
        "inventory.update": f"{base}/api/v1/webhooks/lightspeed/inventory.update/",
        "product.update":   f"{base}/api/v1/webhooks/lightspeed/product.update/",
        "customer.update":  f"{base}/api/v1/webhooks/lightspeed/customer.update/",
        "sale.update":      f"{base}/api/v1/webhooks/lightspeed/sale.update/",
    }
    result = ensure_many(desired, active=True)
    return JsonResponse(result, safe=False)

def credit_check(request):
    """
    Placeholder for credit check endpoint.
    {
        "data": "354fb701-6f36-4d1b-923b-7ab300cc4b5f"
    }
    """
    customer_id = "0698ab21-5fa1-11f0-f6d9-79b259066239"
    response = create_lightspeed_request(method="GET", endpoint=f"store_credits/{customer_id}")
    response_data = response.json()
    return JsonResponse(response_data)

