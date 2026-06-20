"""Role-specific dashboard endpoints: pharmacy, pro, admin-analytics."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends

from core import (
    db, now_utc, require_roles,
    ROLE_PHARMACY, ROLE_OWNER_DOCTOR, ROLE_ADMIN, ROLE_PRO,
    STATUS_CLOSED, STATUS_SENT_PHARMACY, STATUS_IN_PHARMACY,
    STATUS_READY_BILLING, STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID,
)

router = APIRouter()


def _today_bounds_utc():
    """Return (start_iso, end_iso) for "today" in IST (UTC+05:30)."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    end_ist = start_ist + timedelta(days=1)
    return start_ist.astimezone(timezone.utc).isoformat(), end_ist.astimezone(timezone.utc).isoformat()


@router.get("/pharmacy/dashboard")
async def pharmacy_dashboard(user: dict = Depends(require_roles(ROLE_PHARMACY, ROLE_OWNER_DOCTOR, ROLE_ADMIN))):
    start_iso, end_iso = _today_bounds_utc()
    pending = await db.cases.count_documents({"status": {"$in": [STATUS_SENT_PHARMACY, STATUS_IN_PHARMACY]}})
    dispensed_today = await db.pharmacy_dispense.count_documents({"updated_at": {"$gte": start_iso, "$lt": end_iso}})
    pipeline = [
        {"$match": {"updated_at": {"$gte": start_iso, "$lt": end_iso}}},
        {"$group": {"_id": None, "total": {"$sum": "$medicine_amount"}}},
    ]
    agg = await db.pharmacy_dispense.aggregate(pipeline).to_list(1)
    medicine_revenue_today = agg[0]["total"] if agg else 0
    pharmacy_reminders_pending = await db.reminders.count_documents({
        "audience": "PHARMACY", "status": "PENDING",
    })
    return {
        "pending_dispense_count": pending,
        "dispensed_today_count": dispensed_today,
        "medicine_revenue_today": medicine_revenue_today,
        "pharmacy_reminders_pending": pharmacy_reminders_pending,
    }


@router.get("/pro/dashboard")
async def pro_dashboard(user: dict = Depends(require_roles(ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_ADMIN))):
    start_iso, end_iso = _today_bounds_utc()

    today_pipeline = [
        {"$match": {"updated_at": {"$gte": start_iso, "$lt": end_iso}, "payment_status": "PAID"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}, "n": {"$sum": 1}}},
    ]
    today_agg = await db.payments.aggregate(today_pipeline).to_list(1)
    today_revenue = today_agg[0]["total"] if today_agg else 0
    today_collections = today_agg[0]["n"] if today_agg else 0

    total_pipeline = [{"$match": {"payment_status": "PAID"}}, {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}}]
    total_agg = await db.payments.aggregate(total_pipeline).to_list(1)
    total_revenue = total_agg[0]["total"] if total_agg else 0

    outstanding_pipeline = [
        {"$match": {"payment_status": {"$in": ["UNPAID", "PARTIAL"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$balance_amount"}, "n": {"$sum": 1}}},
    ]
    out_agg = await db.payments.aggregate(outstanding_pipeline).to_list(1)
    outstanding_amount = out_agg[0]["total"] if out_agg else 0
    outstanding_count = out_agg[0]["n"] if out_agg else 0

    total_patients = await db.patients.count_documents({})
    pending_billing = await db.cases.count_documents({
        "status": {"$in": [STATUS_READY_BILLING, STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID]}
    })

    # Revenue per mode today
    mode_pipeline = [
        {"$match": {"updated_at": {"$gte": start_iso, "$lt": end_iso}, "payment_status": "PAID"}},
        {"$group": {"_id": "$payment_mode", "total": {"$sum": "$amount_paid"}}},
    ]
    mode_agg = await db.payments.aggregate(mode_pipeline).to_list(20)
    by_mode_today = {(m["_id"] or "OTHER"): m["total"] for m in mode_agg}

    # 7-day revenue trend (IST days)
    ist = timezone(timedelta(hours=5, minutes=30))
    trend = []
    for i in range(6, -1, -1):
        day_ist = datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        s = day_ist.astimezone(timezone.utc).isoformat()
        e = (day_ist + timedelta(days=1)).astimezone(timezone.utc).isoformat()
        agg = await db.payments.aggregate([
            {"$match": {"updated_at": {"$gte": s, "$lt": e}, "payment_status": "PAID"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}},
        ]).to_list(1)
        trend.append({"date": day_ist.strftime("%Y-%m-%d"), "label": day_ist.strftime("%a"), "revenue": agg[0]["total"] if agg else 0})

    # Follow-ups due today
    followups_today_pipeline = {
        "scheduled_at": {"$gte": start_iso, "$lt": end_iso},
        "status": {"$in": ["PENDING", "SENT"]},
    }
    followups_today = await db.reminders.count_documents(followups_today_pipeline)
    followup_items = await db.reminders.find(followups_today_pipeline, {"_id": 0}).sort("scheduled_at", 1).limit(20).to_list(20)

    return {
        "today_revenue": today_revenue,
        "today_collections": today_collections,
        "total_revenue": total_revenue,
        "total_patients": total_patients,
        "pending_billing_count": pending_billing,
        "outstanding_amount": outstanding_amount,
        "outstanding_count": outstanding_count,
        "by_mode_today": by_mode_today,
        "revenue_trend_7d": trend,
        "followups_today_count": followups_today,
        "followups_today": followup_items,
    }


@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OWNER_DOCTOR))):
    ist = timezone(timedelta(hours=5, minutes=30))

    # 30-day case trend
    case_trend = []
    for i in range(29, -1, -1):
        day_ist = datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        s = day_ist.astimezone(timezone.utc).isoformat()
        e = (day_ist + timedelta(days=1)).astimezone(timezone.utc).isoformat()
        count = await db.cases.count_documents({"created_at": {"$gte": s, "$lt": e}})
        rev_agg = await db.payments.aggregate([
            {"$match": {"updated_at": {"$gte": s, "$lt": e}, "payment_status": "PAID"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}},
        ]).to_list(1)
        case_trend.append({
            "date": day_ist.strftime("%Y-%m-%d"),
            "label": day_ist.strftime("%d %b"),
            "cases": count,
            "revenue": rev_agg[0]["total"] if rev_agg else 0,
        })

    # By role login activity (last 30 days)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    login_pipeline = [
        {"$match": {"action": "LOGIN", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$actor_role", "count": {"$sum": 1}}},
    ]
    login_agg = await db.audit_logs.aggregate(login_pipeline).to_list(20)
    logins_by_role = {a["_id"]: a["count"] for a in login_agg if a["_id"]}

    # Top complaints (very simple: take first 3 words of each complaint, count)
    cases = await db.cases.find({}, {"_id": 0, "complaint_text": 1}).limit(5000).to_list(5000)
    word_counts: dict[str, int] = {}
    for c in cases:
        words = (c.get("complaint_text") or "").lower().split()
        for w in words:
            w = w.strip(".,;:()[]\"'!? ").lstrip("-")
            if len(w) >= 4 and w not in {"with", "from", "have", "been", "pain", "patient", "this", "that", "since", "very", "having"}:
                word_counts[w] = word_counts.get(w, 0) + 1
    top_complaints = sorted(word_counts.items(), key=lambda x: -x[1])[:10]

    # Average consultation-to-billing turnaround (minutes) for closed cases in last 30 days
    closed_cases = await db.cases.find({
        "status": STATUS_CLOSED,
        "closed_at": {"$gte": cutoff},
        "consultation_started_at": {"$exists": True},
    }, {"_id": 0, "consultation_started_at": 1, "closed_at": 1}).to_list(500)
    durations = []
    for c in closed_cases:
        try:
            s = datetime.fromisoformat(c["consultation_started_at"].replace("Z", "+00:00"))
            e = datetime.fromisoformat(c["closed_at"].replace("Z", "+00:00"))
            durations.append((e - s).total_seconds() / 60.0)
        except Exception:
            continue
    avg_turnaround_min = round(sum(durations) / len(durations), 1) if durations else 0

    return {
        "case_trend_30d": case_trend,
        "logins_by_role_30d": logins_by_role,
        "top_complaints": [{"term": t, "count": n} for t, n in top_complaints],
        "avg_turnaround_minutes": avg_turnaround_min,
        "closed_cases_30d": len(closed_cases),
    }
