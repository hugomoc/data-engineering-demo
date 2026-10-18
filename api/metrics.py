"""Deterministic ecommerce metrics and quota fallback summaries."""

def compute_revenue_delta(monthly_data):
    """Compare the latest two months of revenue for trend questions."""

    if not monthly_data or len(monthly_data) < 2:
        return {
            "error": "Need at least 2 months of data"
        }

    sorted_data = sorted(monthly_data, key=lambda x: x["month"])

    prev = sorted_data[-2]
    curr = sorted_data[-1]

    delta = curr["revenue"] - prev["revenue"]
    pct_change = (delta / prev["revenue"]) * 100 if prev["revenue"] else 0

    return {
        "previous_month": prev,
        "current_month": curr,
        "absolute_change": delta,
        "percent_change": pct_change
    }


def compute_product_contribution(top_products):
    """Calculate each product's share of returned product revenue."""

    total = sum(p["revenue"] for p in top_products)

    return [
        {
            "product": p["product_name"],
            "revenue": p["revenue"],
            "share": (p["revenue"] / total) * 100 if total else 0
        }
        for p in top_products
    ]


def compute_segment_contribution(segments):
    """Calculate each customer segment's share of returned revenue."""

    total = sum(s["revenue"] for s in segments)

    return [
        {
            "segment": s["segment"],
            "revenue": s["revenue"],
            "share": (s["revenue"] / total) * 100 if total else 0
        }
        for s in segments
    ]


def detect_sales_anomalies(monthly_data):
    """Flag months whose revenue falls below 80% of the average month."""

    if not monthly_data:
        return []

    anomalies = []

    revenues = [r["revenue"] for r in monthly_data]

    avg = sum(revenues) / len(revenues)

    for row in monthly_data:

        if row["revenue"] < avg * 0.8:
            anomalies.append({
                "month": row["month"],
                "revenue": row["revenue"],
                "reason": "Below expected range"
            })

    return anomalies


def build_fallback_summary(metrics):
    """Summarize only computed metrics when the model quota is exhausted."""
    sections = ["Executive Summary"]
    revenue = metrics.get("revenue_delta")
    if revenue and "error" not in revenue:
        direction = "increased" if revenue["absolute_change"] >= 0 else "decreased"
        sections.append(
            f"Revenue {direction} from ${revenue['previous_month']['revenue']:,.0f} "
            f"to ${revenue['current_month']['revenue']:,.0f}, "
            f"a change of {revenue['percent_change']:.1f}%."
        )
    products = metrics.get("product_contribution")
    if products:
        top = products[0]
        sections.append(
            f"Top Product: {top['product']} generated ${top['revenue']:,.0f} "
            f"and contributed {top['share']:.1f}% of product revenue."
        )
    segments = metrics.get("segment_contribution")
    if segments:
        top = max(segments, key=lambda row: row["share"])
        sections.append(
            f"Top Customer Segment: {top['segment']} contributed "
            f"{top['share']:.1f}% of total revenue."
        )
    if "anomalies_sales" in metrics:
        sections.append(f"Anomalies: {len(metrics['anomalies_sales'])} unusual month(s) detected.")
    return "\n\n".join(sections)
