import requests
from decouple import config
from datetime import datetime, timedelta

domain = config('LIGHTSPEED_DOMAIN')
bearer_token = config('LIGHTSPEED_API_TOKEN')
# Create a session object
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
})

# Create a base request that always needs to call whenever calling lightspeed
def create_lightspeed_request(method, endpoint, json=None, version=2.0, params=None, headers=None):
    """
    Args:
        method (str): HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE').
        endpoint (str): API endpoint to be appended to the base URL.
        json (dict, optional): JSON data to send in the body of the request.
        version (float or str, optional): API version to use in the URL. Defaults to 2.0.
        params (dict, optional): Query parameters to include in the request.
        headers (dict, optional): Additional headers to include in the request.

    Returns:
        requests.Response: The response object returned by the requests library.
    """
    url = f"https://{domain}.retail.lightspeed.app/api/{version}/{endpoint}"
    # Merge session headers with custom headers, if provided
    request_headers = session.headers.copy()
    if headers:
        request_headers.update(headers)
    response = session.request(method, url, json=json, params=params, headers=request_headers)
    return response

def get_daily_sales_report(date=None):
    """
    Get sales report for a specific day.
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format. Defaults to today.
    
    Returns:
        requests.Response: Sales data for the specified day or current day.
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    params = {
        'type': 'sales',
        'date_from': f"{date}T00:00:00Z",
        'date_to': f"{date}T23:59:59Z"
    }
    
    return create_lightspeed_request('GET', 'search', params=params)

def get_weekly_sales_report(start_date=None):
    """
    Get sales report for a week starting from the specified date.
    
    Args:
        start_date (str, optional): Start date in YYYY-MM-DD format. Defaults to start of current week.
    
        Returns:
        requests.Response: Sales data for the specified week or current week.
    """
    if start_date is None:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        start_date = start_of_week.strftime('%Y-%m-%d')
    
    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
    end_datetime = start_datetime + timedelta(days=6)
    
    params = {
        'type': 'sales',
        'date_from': f"{start_date}T00:00:00Z",
        'date_to': f"{end_datetime.strftime('%Y-%m-%d')}T23:59:59Z"
    }
    
    return create_lightspeed_request('GET', 'search', params=params)

def get_monthly_sales_report(year=None, month=None):
    """
    Get sales report for a specific month.
    
    Args:
        year (int, optional): Year. Defaults to current year.
        month (int, optional): Month (1-12). Defaults to current month.
    
    Returns:
        requests.Response: Sales data for the specified month or current month.
    """
    if year is None or month is None:
        now = datetime.now()
        year = year or now.year
        month = month or now.month
    
    # First day of the month
    start_date = datetime(year, month, 1)
    
    # Last day of the month
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    params = {
        'type': 'sales',
        'date_from': f"{start_date.strftime('%Y-%m-%d')}T00:00:00Z",
        'date_to': f"{end_date.strftime('%Y-%m-%d')}T23:59:59Z"
    }
    
    return create_lightspeed_request('GET', 'search', params=params)

