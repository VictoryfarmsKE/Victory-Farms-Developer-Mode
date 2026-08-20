import csv
import io

import frappe
from frappe.utils import add_days, flt, format_datetime, get_datetime, getdate, nowdate

# ---------------------------------------------------------------------------
# CONFIG -- safe to edit. These control what gets flagged and who is notified.
# ---------------------------------------------------------------------------

# Flag a transition if EITHER threshold is exceeded (user choice: "both").
# Set ABSOLUTE_THRESHOLD = None to match the manual report exactly (percentage only).
PERCENT_THRESHOLD = 10.0          # flag if |% change| > 10%
ABSOLUTE_THRESHOLD = 20.0         # flag if |rate change| > 20 KSH (set None to disable)

# Restrict analysis to one Item Group, or None for ALL items in the system.
# Set to "Gutted Fish-Tilapia" to reproduce the manual gutted-fish report.
ITEM_GROUP_FILTER = None

# How far back to look for the "previous" rate of an item x warehouse.
LOOKBACK_DAYS = 90

# How many rows to show in the "by warehouse" and "anomalies" sections.
TOP_WAREHOUSES_N = 15
ANOMALY_TOP_N = 15

# TEST: while validating, send only to yourself. Replace with the Finance
# distribution list once the output is approved.
RECIPIENTS = ["christinek@victoryfarmskenya.com"]
ALWAYS_BCC = None


def _severity(abs_pct):
    if abs_pct >= 100.0:
        return "CRITICAL"
    if abs_pct >= 50.0:
        return "HIGH"
    if abs_pct >= 25.0:
        return "MEDIUM"
    if abs_pct >= PERCENT_THRESHOLD:
        return "LOW"
    return None


def analyse_valuation_fluctuations(analysis_date=None):
    """Analyse consecutive valuation-rate transitions per Item x Warehouse for a
    single day and return a structured result dict. No email is sent here, so this
    is safe to call directly for testing/inspection."""
    day = getdate(analysis_date) if analysis_date else add_days(getdate(nowdate()), -1)
    lookback = add_days(day, -LOOKBACK_DAYS)
    start_dt = get_datetime("{} 00:00:00".format(day))
    end_dt = get_datetime("{} 23:59:59".format(day))

    params = {
        "lookback": lookback,
        "day": day,
        "start": start_dt,
        "end": end_dt,
    }

    item_group_clause = ""
    if ITEM_GROUP_FILTER:
        item_group_clause = (
            " AND item_code IN (SELECT name FROM `tabItem` WHERE item_group = %(item_group)s)"
        )
        params["item_group"] = ITEM_GROUP_FILTER

    # LAG() gives the previous valuation rate for the same item x warehouse.
    # The outer filter keeps only transitions whose NEW entry falls in the day.
    rows = frappe.db.sql(
        """
        SELECT item_code, warehouse, posting_dt, prev_rate, new_rate
        FROM (
            SELECT
                item_code,
                warehouse,
                valuation_rate AS new_rate,
                LAG(valuation_rate) OVER (
                    PARTITION BY item_code, warehouse
                    ORDER BY posting_date, posting_time, creation
                ) AS prev_rate,
                TIMESTAMP(posting_date, posting_time) AS posting_dt
            FROM `tabStock Ledger Entry`
            WHERE is_cancelled = 0
              AND posting_date BETWEEN %(lookback)s AND %(day)s
              AND TIMESTAMP(posting_date, posting_time) <= %(end)s
              {item_group_clause}
        ) t
        WHERE t.posting_dt BETWEEN %(start)s AND %(end)s
          AND t.prev_rate IS NOT NULL
        ORDER BY t.posting_dt
        """.format(item_group_clause=item_group_clause),
        params,
        as_dict=True,
    )

    flagged = []
    total_transitions = 0

    for r in rows:
        total_transitions += 1
        prev_rate = flt(r.prev_rate)
        new_rate = flt(r.new_rate)
        abs_change = abs(new_rate - prev_rate)

        if prev_rate == 0:
            # Rate established from zero -> always significant.
            pct = None
            abs_pct = float("inf")
        else:
            pct = (new_rate - prev_rate) / prev_rate * 100.0
            abs_pct = abs(pct)

        flag = abs_pct > PERCENT_THRESHOLD
        if ABSOLUTE_THRESHOLD is not None:
            flag = flag or abs_change > ABSOLUTE_THRESHOLD
        if not flag:
            continue

        flagged.append({
            "item_code": r.item_code,
            "warehouse": r.warehouse,
            "posting_dt": r.posting_dt,
            "prev_rate": prev_rate,
            "new_rate": new_rate,
            "abs_change": abs_change,
            "pct": pct,
            "abs_pct": abs_pct,
            "severity": "CRITICAL" if prev_rate == 0 else _severity(abs_pct),
        })

    # Aggregate by item
    by_item = {}
    for f in flagged:
        agg = by_item.setdefault(f["item_code"], {"count": 0, "max_abs_pct": 0.0})
        agg["count"] += 1
        if f["abs_pct"] != float("inf"):
            agg["max_abs_pct"] = max(agg["max_abs_pct"], f["abs_pct"])

    # Aggregate by warehouse
    by_wh = {}
    for f in flagged:
        agg = by_wh.setdefault(f["warehouse"], {"count": 0, "max_abs_pct": 0.0})
        agg["count"] += 1
        if f["abs_pct"] != float("inf"):
            agg["max_abs_pct"] = max(agg["max_abs_pct"], f["abs_pct"])

    # Severity counts
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in flagged:
        if f["severity"] in severity_counts:
            severity_counts[f["severity"]] += 1

    # Top anomalies by |% change| (infinities -- from-zero -- come first)
    anomalies = sorted(flagged, key=lambda x: x["abs_pct"], reverse=True)[:ANOMALY_TOP_N]

    return {
        "day": day,
        "total_transitions": total_transitions,
        "flagged_count": len(flagged),
        "unique_items": len({f["item_code"] for f in flagged}),
        "unique_warehouses": len({f["warehouse"] for f in flagged}),
        "severity_counts": severity_counts,
        "by_item": by_item,
        "by_warehouse": by_wh,
        "anomalies": anomalies,
        "flagged": flagged,
    }


def _fmt_pct(value):
    if value is None or value == float("inf"):
        return "from 0"
    return "{:,.1f}%".format(value)


def _build_html(data):
    sev = data["severity_counts"]
    item_rows = sorted(data["by_item"].items(), key=lambda kv: kv[1]["count"], reverse=True)
    wh_rows = sorted(
        data["by_warehouse"].items(), key=lambda kv: kv[1]["count"], reverse=True
    )[:TOP_WAREHOUSES_N]

    group_label = ITEM_GROUP_FILTER or "All Items"
    threshold_label = "&gt; {:.0f}% change".format(PERCENT_THRESHOLD)
    if ABSOLUTE_THRESHOLD is not None:
        threshold_label += " or &gt; {:.0f} KSH change".format(ABSOLUTE_THRESHOLD)
    threshold_label += " between consecutive valuation rates (same Item x Warehouse)"

    html = []
    html.append("<h2>Valuation Rate Change Analysis</h2>")
    html.append("<p><b>Company:</b> Victory Farms Ltd<br>")
    html.append("<b>Item scope:</b> {}<br>".format(group_label))
    html.append("<b>Analysis date:</b> {}<br>".format(data["day"]))
    html.append("<b>Threshold:</b> {}</p>".format(threshold_label))

    html.append("<h3>Key Metrics</h3>")
    html.append("<table border='1' cellpadding='6' cellspacing='0'>")
    html.append("<tr><td>Total transitions analysed</td><td>{:,}</td></tr>".format(data["total_transitions"]))
    html.append("<tr><td>Flagged transitions</td><td>{:,}</td></tr>".format(data["flagged_count"]))
    html.append("<tr><td>Unique items flagged</td><td>{}</td></tr>".format(data["unique_items"]))
    html.append("<tr><td>Unique warehouses flagged</td><td>{}</td></tr>".format(data["unique_warehouses"]))
    html.append("<tr><td>CRITICAL (&ge;100%)</td><td>{:,}</td></tr>".format(sev["CRITICAL"]))
    html.append("<tr><td>HIGH (50-100%)</td><td>{:,}</td></tr>".format(sev["HIGH"]))
    html.append("<tr><td>MEDIUM (25-50%)</td><td>{:,}</td></tr>".format(sev["MEDIUM"]))
    html.append("<tr><td>LOW (10-25%)</td><td>{:,}</td></tr>".format(sev["LOW"]))
    html.append("</table>")

    html.append("<h3>Flagged transitions by Item</h3>")
    html.append("<table border='1' cellpadding='6' cellspacing='0'>")
    html.append("<tr><th>Item</th><th>Flagged count</th><th>Max |% change|</th></tr>")
    for item, agg in item_rows:
        html.append(
            "<tr><td>{}</td><td>{:,}</td><td>{:,.1f}%</td></tr>".format(
                item, agg["count"], agg["max_abs_pct"]
            )
        )
    html.append("</table>")

    html.append("<h3>Top {} Warehouses by flagged transitions</h3>".format(TOP_WAREHOUSES_N))
    html.append("<table border='1' cellpadding='6' cellspacing='0'>")
    html.append("<tr><th>Warehouse</th><th>Flagged count</th><th>Max |% change|</th></tr>")
    for wh, agg in wh_rows:
        html.append(
            "<tr><td>{}</td><td>{:,}</td><td>{:,.1f}%</td></tr>".format(
                wh, agg["count"], agg["max_abs_pct"]
            )
        )
    html.append("</table>")

    html.append("<h3>Likely data-entry anomalies (largest swings)</h3>")
    html.append("<table border='1' cellpadding='6' cellspacing='0'>")
    html.append("<tr><th>Date/Time</th><th>Item</th><th>Warehouse</th><th>Prev rate</th><th>New rate</th><th>% change</th></tr>")
    for a in data["anomalies"]:
        html.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{:,.2f}</td><td>{:,.2f}</td><td>{}</td></tr>".format(
                format_datetime(a["posting_dt"]),
                a["item_code"],
                a["warehouse"],
                a["prev_rate"],
                a["new_rate"],
                _fmt_pct(a["pct"]),
            )
        )
    html.append("</table>")

    return "".join(html)


def _build_csv(data):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date/Time", "Item", "Warehouse", "Prev Rate", "New Rate", "Abs Change", "% Change", "Severity"])
    for f in sorted(data["flagged"], key=lambda x: x["abs_pct"], reverse=True):
        writer.writerow([
            format_datetime(f["posting_dt"]),
            f["item_code"],
            f["warehouse"],
            "{:.2f}".format(f["prev_rate"]),
            "{:.2f}".format(f["new_rate"]),
            "{:.2f}".format(f["abs_change"]),
            _fmt_pct(f["pct"]),
            f["severity"],
        ])
    return buf.getvalue()


@frappe.whitelist()
def check_valuation_fluctuations(analysis_date=None, recipients=None):
    """Daily 6am scheduler job. Analyses the previous day's valuation-rate
    transitions, and if anything is flagged, emails Finance an HTML summary plus
    a CSV of every flagged transition.

    Args (optional, for manual testing):
        analysis_date: 'YYYY-MM-DD' to analyse a specific day instead of yesterday.
        recipients:    comma-separated emails to override the configured list.
    """
    try:
        data = analyse_valuation_fluctuations(analysis_date)

        if not data["flagged_count"]:
            frappe.log_error(
                "No valuation fluctuations above threshold for {}.".format(data["day"]),
                "Valuation Fluctuation Report",
            )
            return {"status": "ok", "flagged": 0, "day": str(data["day"])}

        to = RECIPIENTS
        if recipients:
            to = [e.strip() for e in recipients.split(",") if e.strip()]

        subject = "Valuation Rate Fluctuation Alert - {} ({} flagged)".format(
            data["day"], data["flagged_count"]
        )
        frappe.sendmail(
            recipients=to,
            bcc=ALWAYS_BCC,
            subject=subject,
            message=_build_html(data),
            attachments=[{
                "fname": "valuation_fluctuations_{}.csv".format(data["day"]),
                "fcontent": _build_csv(data),
            }],
            now=True,
        )
        return {"status": "sent", "flagged": data["flagged_count"], "day": str(data["day"])}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "check_valuation_fluctuations failed")
        raise
