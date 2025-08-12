import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import requests
from decouple import config


# Configuration
domain = config('LIGHTSPEED_DOMAIN')
bearer_token = config('LIGHTSPEED_API_TOKEN')

# Session setup with authentication headers
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def create_lightspeed_request(
    method: str,
    endpoint: str,
    json: dict = None,
    version: float = 2.0,
    params: dict = None,
    headers: dict = None,
    timeout: int = 30
    ) -> requests.Response:
    
    """
    Create and execute an authenticated HTTP request to the Lightspeed Retail API.
    
    This function constructs the full API URL, merges headers with session defaults,
    and executes the request using the configured session with authentication.
    
    Args:
        method (str): HTTP method (GET, POST, PUT, DELETE, etc.)
        endpoint (str): API endpoint path (without leading slash)
        json (dict, optional): JSON payload for the request body. Defaults to None.
        version (float, optional): API version number. Defaults to 2.0.
        params (dict, optional): URL query parameters. Defaults to None.
        headers (dict, optional): Additional headers to merge with session headers. Defaults to None.
        timeout (int, optional): Request timeout in seconds. Defaults to 30.
    
    Returns:
        requests.Response: The HTTP response object from the API call.
        
    """
    url = f"https://{domain}.retail.lightspeed.app/api/{version}/{endpoint}"
    request_headers = session.headers.copy()
    
    if headers:
        request_headers.update(headers)
    
    return session.request(
        method,
        url,
        json=json,
        params=params,
        headers=request_headers,
        timeout=timeout
    )

def _local_date_to_utc_window(date_str: str, tzname: str = "America/New_York") -> tuple[str, str]:
    """
    Convert a local date string to UTC datetime window spanning the entire day.

    As Lightspeed API works in UTC, we need to convert the local date range to UTC.

    Takes a date in YYYY-MM-DD format and timezone name, then returns the start
    and end of that day in UTC ISO format.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format.
        tzname (str, optional): IANA timezone name. Defaults to "America/New_York".
    
    Returns:
        tuple[str, str]: A tuple containing (start_utc, end_utc) where both are
                        ISO format strings with 'Z' suffix (e.g., "2023-12-01T05:00:00Z").
    """
    tz = ZoneInfo(tzname)
    local_start = datetime.strptime(date_str, "%Y-%m-%d").replace(
        tzinfo=tz, hour=0, minute=0, second=0, microsecond=0
    )
    local_end = local_start + timedelta(days=1)
    
    s_from = local_start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    s_to = local_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    
    return s_from, s_to

def _paged_search_sales(
    date_from_utc: str,
    date_to_utc: str,
    page_size: int = 1000,
    max_pages: int = 1000,
    extra_params: dict | None = None
    ) -> tuple[list, list]:
    """
    Fetch all sales from /api/2.0/search using offset/page_size pagination.
    
    This function handles automatic pagination to retrieve all sales data within
    the specified date range.
    
    Args:
        date_from_utc (str): Start date in UTC ISO format (e.g., "2023-12-01T00:00:00Z").
        date_to_utc (str): End date in UTC ISO format (e.g., "2023-12-02T00:00:00Z").
        page_size (int, optional): Number of items per page. Defaults to 1000.
        max_pages (int, optional): Maximum number of pages to fetch. Defaults to 1000.
        extra_params (dict | None, optional): Additional query parameters. Defaults to None.
    
    Returns:
        tuple[list, list]: A tuple containing:
            - all_items (list): Combined list of all sales items from all pages
            - urls (list): List of request URLs for debugging purposes
    """
    params_base = {
        "type": "sales",
        "date_from": date_from_utc,
        "date_to": date_to_utc
    }
    
    if extra_params:
        params_base.update(extra_params)

    offset = 0
    all_items = []
    urls = []

    for _ in range(max_pages):
        params = dict(params_base, offset=offset, page_size=page_size)
        resp = create_lightspeed_request("GET", "search", params=params)

        if resp.status_code == 429:
            # Respect Retry-After (RFC1123). If missing, back off a bit.
            retry_after = resp.headers.get("Retry-After")
            wait = 5
            
            if retry_after:
                try:
                    wait_dt = datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S %Z")
                    wait = max(1, int((wait_dt - datetime.utcnow()).total_seconds()))
                except Exception:
                    pass
            
            time.sleep(wait)
            continue

        resp.raise_for_status()
        payload = resp.json() or {}
        items = payload.get("data", [])  # Search returns { "data": [...] }
        
        urls.append(resp.request.url)
        all_items.extend(items)

        if len(items) < page_size:
            break
        
        offset += len(items)

    return all_items, urls

class _AggregatedResponse:
    """
    Mimic requests.Response interface for aggregated paginated data.
    
    This class provides a Response-like interface for data that has been aggregated
    from multiple paginated API calls. It maintains compatibility with existing code
    that expects a requests.Response object while providing access to the combined
    data and debugging information.
    
    Attributes:
        status_code (int): HTTP status code (typically 200 for successful aggregation).
        request (SimpleNamespace): Mock request object with URL information.
        request_urls (list): List of all URLs that were requested during aggregation.
    
    Args:
        data_list (list): Combined data from all paginated responses.
        urls (list): List of request URLs used in the aggregation.
        status_code (int, optional): HTTP status code to report. Defaults to 200.
    
    """
    
    def __init__(self, data_list: list, urls: list, status_code: int = 200):
        self.status_code = status_code
        self._data = data_list
        self.request = SimpleNamespace(url=(urls[0] if urls else None))
        self.request_urls = urls

    def json(self) -> dict:
        """
        Return the aggregated data in a format similar to the original API response.
        """
        return {
            "data": self._data,
            "request_urls": self.request_urls
        }

def get_daily_sales_report(
    date: str = None,
    tzname: str = "America/New_York",
    page_size: int = 1000
    ) -> _AggregatedResponse:
    """
    Generate a sales report for a specific day in the specified timezone.
    
    If no date is provided, uses the current date in the specified timezone.
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format. If None, uses current date
                             in the specified timezone. Defaults to None.
        tzname (str, optional): timezone name for date interpretation.
                                Defaults to "America/New_York".
        page_size (int, optional): Number of items per API page. Defaults to 1000.

    """
    if date is None:
        date = datetime.now(ZoneInfo(tzname)).strftime("%Y-%m-%d")
    
    date_from_utc, date_to_utc = _local_date_to_utc_window(date, tzname)
    items, urls = _paged_search_sales(date_from_utc, date_to_utc, page_size=page_size)
    
    return _AggregatedResponse(items, urls, status_code=200)

def get_weekly_sales_report(
    start_date: str = None,
    tzname: str = "America/New_York",
    page_size: int = 1000
    ) -> _AggregatedResponse:
    """
    Calculates the week period from the start date (or current date if not provided)
    through the following Sunday, then retrieves all sales data for that period.
    
    Args:
        start_date (str, optional): Start date in YYYY-MM-DD format. If None, uses
                                   current date in the specified timezone. Defaults to None.
        tzname (str, optional): timezone name for date interpretation.
                                Defaults to "America/New_York".
        page_size (int, optional): Number of items per API page. Defaults to 1000.
    
    Note:
        Week calculation uses Monday=0, Sunday=6. The end date is the next Sunday
        after the start date (inclusive of the full Sunday).

    """
    tz = ZoneInfo(tzname)

    if start_date is None:
        start_local = datetime.now(tz).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        start_local = datetime.strptime(start_date, "%Y-%m-%d").replace(
            tzinfo=tz, hour=0, minute=0, second=0, microsecond=0
        )

    # Calculate how many days until the next Sunday (weekday 6)
    days_until_sunday = 6 - start_local.weekday()
    end_local = start_local + timedelta(days=days_until_sunday + 1)  # +1 to make the end time exclusive

    date_from_utc = start_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    date_to_utc = end_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    items, urls = _paged_search_sales(date_from_utc, date_to_utc, page_size=page_size)
    
    return _AggregatedResponse(items, urls, status_code=200)


def get_monthly_sales_report(
    year: int = None,
    month: int = None,
    tzname: str = "America/New_York",
    page_size: int = 1000
    ) -> _AggregatedResponse:
    """    
    Retrieves all sales data for the specified month. If no year/month is provided,
    uses the current month. For the current month, the report includes data up to
    the current date only.
    
    Args:
        year (int, optional): Year for the report. If None, uses current year.
                             Defaults to None.
        month (int, optional): Month for the report (1-12). If None, uses current month.
                              Defaults to None.
        tzname (str, optional): IANA timezone name for date interpretation.
                               Defaults to "America/New_York".
        page_size (int, optional): Number of items per API page. Defaults to 1000.
   
    """
    now_local = datetime.now(ZoneInfo(tzname))
    year = year or now_local.year
    month = month or now_local.month
    
    tz = ZoneInfo(tzname)
    start_local = datetime(year, month, 1, tzinfo=tz)
    
    # Calculate end of month or current date if it's the current month
    if month == 12:
        end_local = datetime(year + 1, 1, 1, tzinfo=tz)
    else:
        end_local = datetime(year, month + 1, 1, tzinfo=tz)
    
    # For current month, only go up to current date + 1 day
    if year == now_local.year and month == now_local.month:
        end_local = now_local.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
    
    date_from_utc = start_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    date_to_utc = end_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    
    items, urls = _paged_search_sales(date_from_utc, date_to_utc, page_size=page_size)
    
    return _AggregatedResponse(items, urls, status_code=200)
