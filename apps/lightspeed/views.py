from django.http import JsonResponse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

from .api import (
    SalesReportProcessor
)

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
        # report_data = processor.generate_report("daily", date="2025-08-08")
        
        # Weekly Report  
        # report_data = processor.generate_report("weekly", start_date="2025-07-14")
        
        # Monthly Report (current example)
        report_data = processor.generate_report("monthly", year=2025, month=7)
        
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

