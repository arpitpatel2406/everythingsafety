from django.http import JsonResponse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

from .api import (
    get_daily_sales_report,
    get_weekly_sales_report,
    get_monthly_sales_report,
)

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
"""
2025-08-11 -> $4500 mismatch for unknown reason
2025-07-18 -> $400  mismatch for unknown reason
"""
def get_sales(_request=None):
    try:
        date_str = "2025-08-08"          # reporting day (local)
        tzname   = "America/New_York"    # default US reporting TZ

        # DAY fetch (UTC window for the local day)
        # response = get_daily_sales_report(date=date_str, tzname=tzname)
        # For week/month later, just swap this line:
        response = get_monthly_sales_report(year=2025, month=7, tzname=tzname)
        # response = get_weekly_sales_report(start_date="2025-07-14", tzname=tzname)
        # response = get_daily_sales_report(date="2025-07-18")

        if response.status_code != 200:
            return JsonResponse(
                {"error": f"Failed to retrieve sales data for {date_str}"},
                status=response.status_code
            )

        data = response.json()
        with open("data.json", "w") as f:
            json.dump(data, f, indent=2)
        sales = data.get("data", [])
        print(f"Fetched {len(sales)} sales records for {date_str} in {tzname} timezone.")
        # De-dupe by sale id
        dedup = {s.get("id"): s for s in sales if s.get("id")}
        sales_unique = list(dedup.values())

        # Debug counts
        raw_count = len(sales)
        unique_count = len(sales_unique)
        status_counts = Counter(s.get("status") for s in sales_unique)
        state_counts  = Counter(s.get("state")  for s in sales_unique)

        # Sale-level filter
        filtered_sales = []
        for s in sales_unique:
            status = s.get("status")
            state  = s.get("state")

            if status in {"SAVED", "VOIDED"}:
                continue
            if status == "ONACCOUNT_CLOSED" and state != "closed":
                continue
            if state == "voided":
                continue

            filtered_sales.append(s)


        # Totals (global) – will update ONCE per line
        totals = {
            "gross_sales": 0.0, "returns_sales": 0.0,
            "gross_tax":   0.0, "returns_tax":   0.0,
            "gross_cost":  0.0, "returns_cost":  0.0,
            "gross_profit":0.0, "returns_profit":0.0,
            "total_discount": 0.0,
            "return_lines_seen": 0,
            "negative_lines_seen": 0,
        }

        # Buckets
        def _blank_bucket():
            return {
                "count_sales_gross": 0, "count_sales_net": 0,
                "gross_sales": 0.0, "gross_tax": 0.0, "gross_cost": 0.0, "gross_profit": 0.0,
                "returns_sales": 0.0, "returns_tax": 0.0, "returns_cost": 0.0, "returns_profit": 0.0,
                "net_sales": 0.0, "net_tax": 0.0, "net_cost": 0.0, "net_profit": 0.0,
            }

        daily_by_date  = defaultdict(_blank_bucket)  # local 'YYYY-MM-DD'
        hourly_by_hour = defaultdict(_blank_bucket)  # local 'HH'

        # helpers: split bucket vs totals so totals are not double-counted
        def _acc_bucket(bucket, kind, sales_amt, tax_amt, cost_amt):
            bucket[f"{kind}_sales"]  += sales_amt
            bucket[f"{kind}_tax"]    += tax_amt
            bucket[f"{kind}_cost"]   += cost_amt
            bucket[f"{kind}_profit"] += (sales_amt - cost_amt)

        def _acc_totals(kind, sales_amt, tax_amt, cost_amt):
            totals[f"{kind}_sales"]  += sales_amt
            totals[f"{kind}_tax"]    += tax_amt
            totals[f"{kind}_cost"]   += cost_amt
            totals[f"{kind}_profit"] += (sales_amt - cost_amt)

        # (optional) sale-level cross-check (net)
        ls_net_sales_sum = 0.0
        ls_net_tax_sum   = 0.0

        for s in filtered_sales:
            ls_net_sales_sum += _money(s.get("total_price"))
            ls_net_tax_sum   += _money(s.get("total_tax"))

            line_items = s.get("line_items") or []

            local_dt = _to_local_dt(s.get("sale_date") or "", tzname)
            day  = local_dt.strftime("%Y-%m-%d") if local_dt else "unknown"
            hour = local_dt.strftime("%H")       if local_dt else "??"

            b_day  = daily_by_date[day]
            b_hour = hourly_by_hour[hour]

            had_positive = False
            had_any = False

            for item in line_items:
                had_any = True
                qty   = _money(item.get("quantity"))
                price = _money(item.get("total_price"))
                tax   = _money(item.get("total_tax"))
                cost  = _money(item.get("total_cost"))
                totals["total_discount"] += _money(item.get("total_discount"))

                is_return   = _is_true(item.get("is_return"))
                is_negative = (qty < 0) or (price < 0) or (tax < 0) or (cost < 0)

                if is_return:
                    totals["return_lines_seen"] += 1
                if is_negative:
                    totals["negative_lines_seen"] += 1

                kind = "returns" if (is_return or is_negative) else "gross"

                # update buckets (day+hour)
                _acc_bucket(b_day,  kind, price, tax, cost)
                _acc_bucket(b_hour, kind, price, tax, cost)

                # update global totals ONCE per line
                _acc_totals(kind, price, tax, cost)

                if kind == "gross":
                    had_positive = True

            if had_positive:
                b_day["count_sales_gross"]  += 1
                b_hour["count_sales_gross"] += 1
            if had_any:
                b_day["count_sales_net"]  += 1
                b_hour["count_sales_net"] += 1

        # finalize net per-bucket
        def _finalize_bucket(b):
            b["net_sales"]  = b["gross_sales"]  + b["returns_sales"]
            b["net_tax"]    = b["gross_tax"]    + b["returns_tax"]
            b["net_cost"]   = b["gross_cost"]   + b["returns_cost"]
            b["net_profit"] = b["net_sales"] - b["net_cost"]

        for b in daily_by_date.values():
            _finalize_bucket(b)
        for b in hourly_by_hour.values():
            _finalize_bucket(b)

        # round buckets
        def _round_bucket(b):
            for k, v in list(b.items()):
                if isinstance(v, float):
                    b[k] = round(v, 2)
            return b

        daily_sorted  = dict(sorted(((d, _round_bucket(v)) for d, v in daily_by_date.items()), key=lambda x: x[0]))
        hourly_sorted = dict(sorted(((h, _round_bucket(v)) for h, v in hourly_by_hour.items()), key=lambda x: x[0]))

        # derive NET totals
        totals_net = {
            "sales":  round(totals["gross_sales"] + totals["returns_sales"], 2),
            "tax":    round(totals["gross_tax"]   + totals["returns_tax"],   2),
            "cost":   round(totals["gross_cost"]  + totals["returns_cost"],  2),
            "profit": round(
                (totals["gross_sales"] + totals["returns_sales"])
                - (totals["gross_cost"]  + totals["returns_cost"]), 2
            ),
        }

        # round global totals
        for k in list(totals.keys()):
            if isinstance(totals[k], float):
                totals[k] = round(totals[k], 2)

        return JsonResponse({
            "params_used": {"date": date_str, "tz": tzname, "period": "day"},
            "raw_count": raw_count,
            "unique_count": unique_count,
            "status_counts": dict(status_counts),
            "state_counts": dict(state_counts),
            "filtered_count": len(filtered_sales),

            "totals": {
                "gross":   {"sales": totals["gross_sales"],   "tax": totals["gross_tax"],   "cost": totals["gross_cost"],   "profit": totals["gross_profit"]},
                "returns": {"sales": totals["returns_sales"], "tax": totals["returns_tax"], "cost": totals["returns_cost"], "profit": totals["returns_profit"]},
                "net":     totals_net,
                "total_discount": totals["total_discount"],
                "return_lines_seen": totals["return_lines_seen"],
                "negative_lines_seen": totals["negative_lines_seen"],
            },

            "daily":  daily_sorted,     # local 'YYYY-MM-DD'
            "hourly": hourly_sorted,    # local 'HH'

            # helps verify fetch window
            "lightspeed_request_url": getattr(response.request, "url", None),

            # sale-level field sums to cross-check NET
            "lightspeed_net_crosscheck": {
                "sum_sale_total_price": round(ls_net_sales_sum, 2),
                "sum_sale_total_tax":   round(ls_net_tax_sum, 2),
                "note": "Close to totals.net.sales/tax if you include returns/negatives."
            },
            "notes": [
                "Gross = positive lines only; Returns = negative/is_return lines; Net = Gross + Returns.",
                "Sale-level filters: exclude SAVED/VOIDED/ONACCOUNT_CLOSED and state=voided.",
                "Dates/hours are converted to America/New_York BEFORE bucketing.",
            ]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
