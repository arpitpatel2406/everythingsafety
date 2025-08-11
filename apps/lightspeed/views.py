from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .api import get_daily_sales_report
import json
import pandas as pd

@require_http_methods(["GET"])
@csrf_exempt
def get_sales(request):
    """
    Get sales from Lightspeed API and return summary
    """
    try:
        response = get_daily_sales_report("2025-08-01")

        if response.status_code == 200:
            data = response.json()

            # ✅ safely access the 'data' array
            if "data" not in data:
                return JsonResponse({'error': 'Missing "data" in response'}, status=500)

            sales = data["data"]
            total_sales = 0.0
            total_tax = 0.0
            total_cost = 0.0

            for sale in sales:
                total_sales += sale.get("total_price", 0)
                total_tax += sale.get("total_tax", 0)
                for item in sale.get("line_items", []):
                    total_cost += item.get("total_cost", 0)

            gross_profit = total_sales - total_cost

            return JsonResponse({
                "total_sales": round(total_sales, 2),
                "total_tax": round(total_tax, 2),
                "gross_profit": round(gross_profit, 2)
            })

        else:
            return JsonResponse({'error': 'Failed to retrieve sales data'}, status=response.status_code)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
