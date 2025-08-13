import time
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict

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

DEFAULT_TIMEZONE = "America/New_York"


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


# Utility Functions
def _is_true(v):
    return (v is True) or (isinstance(v, str) and v.lower() == "true") or (v == 1)

def _money(x):
    try:
        return float(x or 0)
    except Exception:
        return 0.0

def _to_local_dt(iso_str: str, tzname: str):
    if not iso_str:
        return None
    s = iso_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo(tzname))


class SalesReportProcessor:
    """
    sales report processor that handles daily, weekly, and monthly reports
    with consistent data processing and response formatting.
    """
    
    def __init__(self, timezone: str = DEFAULT_TIMEZONE):
        self.timezone = timezone
        
    def generate_report(self, period: str, **kwargs) -> dict:
        """
        Generate sales report for specified period with dynamic parameters.
        
        Args:
            period (str): 'daily', 'weekly', or 'monthly'
            **kwargs: Period-specific parameters
                - daily: date (optional)
                - weekly: start_date (optional)  
                - monthly: year (optional), month (optional)
                
        Returns:
            dict: Processed sales report data
        """
        try:
            # Get API response based on period
            response = self._fetch_sales_data(period, **kwargs)
            
            if response.status_code != 200:
                return {
                    "error": f"Failed to retrieve {period} sales data",
                    "status_code": response.status_code
                }
            
            # Process the response data
            return self._process_sales_data(response, period, **kwargs)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e), "status_code": 500}
    
    def _fetch_sales_data(self, period: str, **kwargs):
        """Fetch sales data from appropriate API based on period."""
        if period == "daily":
            date = kwargs.get('date')
            return get_daily_sales_report(date=date, tzname=self.timezone)
            
        elif period == "weekly":
            start_date = kwargs.get('start_date')
            return get_weekly_sales_report(start_date=start_date, tzname=self.timezone)
            
        elif period == "monthly":
            year = kwargs.get('year')
            month = kwargs.get('month')
            return get_monthly_sales_report(year=year, month=month, tzname=self.timezone)
            
        else:
            raise ValueError(f"Invalid period: {period}. Must be 'daily', 'weekly', or 'monthly'")
    
    def _process_sales_data(self, response, period: str, **kwargs) -> dict:
        """Process raw sales data into structured report format."""
        
        # Extract and save data
        data = response.json()
        with open("data.json", "w") as f:
            json.dump(data, f, indent=2)
            
        sales = data.get("data", [])
        print(f"Fetched {len(sales)} sales records for {period} report in {self.timezone} timezone.")
        
        # Deduplicate by sale ID
        dedup = {s.get("id"): s for s in sales if s.get("id")}
        sales_unique = list(dedup.values())
        
        # Generate debug counts
        raw_count = len(sales)
        unique_count = len(sales_unique)
        status_counts = Counter(s.get("status") for s in sales_unique)
        state_counts = Counter(s.get("state") for s in sales_unique)
        
        # Filter sales
        filtered_sales = self._filter_sales(sales_unique)
        
        # Process sales data
        totals, daily_sorted, hourly_sorted, ls_net_sales_sum, ls_net_tax_sum = self._calculate_metrics(
            filtered_sales, self.timezone
        )
        
        # Build parameters used
        params_used = self._build_params_used(period, kwargs)
        
        # Return structured response
        return {
            "params_used": params_used,
            "raw_count": raw_count,
            "unique_count": unique_count,
            "status_counts": dict(status_counts),
            "state_counts": dict(state_counts),
            "filtered_count": len(filtered_sales),
            "totals": self._format_totals(totals),
            "daily": daily_sorted,
            "hourly": hourly_sorted,
            "lightspeed_request_url": getattr(response.request, "url", None),
            "lightspeed_net_crosscheck": {
                "sum_sale_total_price": round(ls_net_sales_sum, 2),
                "sum_sale_total_tax": round(ls_net_tax_sum, 2),
                "note": "Close to totals.net.sales/tax if you include returns/negatives."
            },
            "notes": [
                "Gross = positive lines only; Returns = negative/is_return lines; Net = Gross + Returns.",
                "Sale-level filters: exclude SAVED/VOIDED/ONACCOUNT_CLOSED and state=voided.",
                f"Dates/hours are converted to {self.timezone} BEFORE bucketing.",
            ]
        }
    
    def _filter_sales(self, sales_unique: list) -> list:
        """Apply business logic filters to sales data."""
        filtered_sales = []
        for s in sales_unique:
            status = s.get("status")
            state = s.get("state")

            if status in {"SAVED", "VOIDED"}:
                continue
            if status == "ONACCOUNT_CLOSED" and state != "closed":
                continue
            if state == "voided":
                continue

            filtered_sales.append(s)
        
        return filtered_sales
    
    def _calculate_metrics(self, filtered_sales: list, tzname: str) -> tuple:
        """Calculate all sales metrics including totals and breakdowns."""
        
        # Initialize totals
        totals = {
            "gross_sales": 0.0, "returns_sales": 0.0,
            "gross_tax": 0.0, "returns_tax": 0.0,
            "gross_cost": 0.0, "returns_cost": 0.0,
            "gross_profit": 0.0, "returns_profit": 0.0,
            "total_discount": 0.0,
            "return_lines_seen": 0,
            "negative_lines_seen": 0,
        }

        # Initialize buckets
        def _blank_bucket():
            return {
                "count_sales_gross": 0, "count_sales_net": 0,
                "gross_sales": 0.0, "gross_tax": 0.0, "gross_cost": 0.0, "gross_profit": 0.0,
                "returns_sales": 0.0, "returns_tax": 0.0, "returns_cost": 0.0, "returns_profit": 0.0,
                "net_sales": 0.0, "net_tax": 0.0, "net_cost": 0.0, "net_profit": 0.0,
            }

        daily_by_date = defaultdict(_blank_bucket)
        # hourly_by_hour = defaultdict(_blank_bucket)

        # Helper functions
        def _acc_bucket(bucket, kind, sales_amt, tax_amt, cost_amt):
            bucket[f"{kind}_sales"] += sales_amt
            bucket[f"{kind}_tax"] += tax_amt
            bucket[f"{kind}_cost"] += cost_amt
            bucket[f"{kind}_profit"] += (sales_amt - cost_amt)

        def _acc_totals(kind, sales_amt, tax_amt, cost_amt):
            totals[f"{kind}_sales"] += sales_amt
            totals[f"{kind}_tax"] += tax_amt
            totals[f"{kind}_cost"] += cost_amt
            totals[f"{kind}_profit"] += (sales_amt - cost_amt)

        # Cross-check sums
        ls_net_sales_sum = 0.0
        ls_net_tax_sum = 0.0

        # Process each sale
        for s in filtered_sales:
            ls_net_sales_sum += _money(s.get("total_price"))
            ls_net_tax_sum += _money(s.get("total_tax"))

            line_items = s.get("line_items") or []
            local_dt = _to_local_dt(s.get("sale_date") or "", tzname)
            day = local_dt.strftime("%Y-%m-%d") if local_dt else "unknown"
            hour = local_dt.strftime("%H") if local_dt else "??"

            b_day = daily_by_date[day]
            # b_hour = hourly_by_hour[hour]

            had_positive = False
            had_any = False

            for item in line_items:
                had_any = True
                qty = _money(item.get("quantity"))
                price = _money(item.get("total_price"))
                tax = _money(item.get("total_tax"))
                cost = _money(item.get("total_cost"))
                totals["total_discount"] += _money(item.get("total_discount"))

                is_return = _is_true(item.get("is_return"))
                is_negative = (qty < 0) or (price < 0) or (tax < 0) or (cost < 0)

                if is_return:
                    totals["return_lines_seen"] += 1
                if is_negative:
                    totals["negative_lines_seen"] += 1

                kind = "returns" if (is_return or is_negative) else "gross"

                # Update buckets and totals
                _acc_bucket(b_day, kind, price, tax, cost)
                # _acc_bucket(b_hour, kind, price, tax, cost)
                _acc_totals(kind, price, tax, cost)

                if kind == "gross":
                    had_positive = True

            # Update sale counts
            if had_positive:
                b_day["count_sales_gross"] += 1
                # b_hour["count_sales_gross"] += 1
            if had_any:
                b_day["count_sales_net"] += 1
                # b_hour["count_sales_net"] += 1

        # Finalize net calculations
        def _finalize_bucket(b):
            b["net_sales"] = b["gross_sales"] + b["returns_sales"]
            b["net_tax"] = b["gross_tax"] + b["returns_tax"]
            b["net_cost"] = b["gross_cost"] + b["returns_cost"]
            b["net_profit"] = b["net_sales"] - b["net_cost"]

        for b in daily_by_date.values():
            _finalize_bucket(b)
        # for b in hourly_by_hour.values():
        #     _finalize_bucket(b)

        # Round and sort buckets
        def _round_bucket(b):
            for k, v in list(b.items()):
                if isinstance(v, float):
                    b[k] = round(v, 2)
            return b

        daily_sorted = dict(sorted(((d, _round_bucket(v)) for d, v in daily_by_date.items()), key=lambda x: x[0]))
        # hourly_sorted = dict(sorted(((h, _round_bucket(v)) for h, v in hourly_by_hour.items()), key=lambda x: x[0]))

        # Round global totals
        for k in list(totals.keys()):
            if isinstance(totals[k], float):
                totals[k] = round(totals[k], 2)

        return totals, daily_sorted, ls_net_sales_sum, ls_net_tax_sum
    
    def _format_totals(self, totals: dict) -> dict:
        """Format totals into structured response format."""
        totals_net = {
            "sales": round(totals["gross_sales"] + totals["returns_sales"], 2),
            "tax": round(totals["gross_tax"] + totals["returns_tax"], 2),
            "cost": round(totals["gross_cost"] + totals["returns_cost"], 2),
            "profit": round(
                (totals["gross_sales"] + totals["returns_sales"])
                - (totals["gross_cost"] + totals["returns_cost"]), 2
            ),
        }
        
        return {
            "gross": {
                "sales": totals["gross_sales"],
                "tax": totals["gross_tax"],
                "cost": totals["gross_cost"],
                "profit": totals["gross_profit"]
            },
            "returns": {
                "sales": totals["returns_sales"],
                "tax": totals["returns_tax"],
                "cost": totals["returns_cost"],
                "profit": totals["returns_profit"]
            },
            "net": totals_net,
            "total_discount": totals["total_discount"],
            "return_lines_seen": totals["return_lines_seen"],
            "negative_lines_seen": totals["negative_lines_seen"],
        }
    
    def _build_params_used(self, period: str, kwargs: dict) -> dict:
        """Build params_used based on period and provided parameters."""
        params = {
            "tz": self.timezone,
            "period": period
        }
        
        if period == "daily":
            params["date"] = kwargs.get('date', datetime.now(ZoneInfo(self.timezone)).strftime("%Y-%m-%d"))
        elif period == "weekly":
            params["start_date"] = kwargs.get('start_date', datetime.now(ZoneInfo(self.timezone)).strftime("%Y-%m-%d"))
        elif period == "monthly":
            now = datetime.now(ZoneInfo(self.timezone))
            params["year"] = kwargs.get('year', now.year)
            params["month"] = kwargs.get('month', now.month)
            
        return params
"""
Professional Sales Report Functions
Usage Examples:
- Daily:   processor = SalesReportProcessor(); data = processor.generate_report("daily", date="2025-08-08")
- Weekly:  processor = SalesReportProcessor(); data = processor.generate_report("weekly", start_date="2025-08-01")
- Monthly: processor = SalesReportProcessor(); data = processor.generate_report("monthly", year=2025, month=7)
"""

