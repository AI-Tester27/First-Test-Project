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

    # Follow-ups due today (strip private clinician notes for non-clinician viewers)
    followups_today_pipeline = {
        "scheduled_at": {"$gte": start_iso, "$lt": end_iso},
        "status": {"$in": ["PENDING", "SENT"]},
    }
    followups_today = await db.reminders.count_documents(followups_today_pipeline)
    raw_followups = await db.reminders.find(followups_today_pipeline, {"_id": 0}).sort("scheduled_at", 1).limit(20).to_list(20)
    is_clinician = user["role"] in (ROLE_OWNER_DOCTOR, ROLE_ADMIN)
    followup_items = []
    for r in raw_followups:
        if is_clinician:
            followup_items.append(r)
        else:
            # PRO viewers see scheduling info but not private clinical notes
            followup_items.append({
                "id": r.get("id"), "patient_name": r.get("patient_name"), "patient_uid": r.get("patient_uid"),
                "scheduled_at": r.get("scheduled_at"), "status": r.get("status"),
            })

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
    now_ist = datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0)
    start_30 = (now_ist - timedelta(days=29)).astimezone(timezone.utc).isoformat()
    end_30 = (now_ist + timedelta(days=1)).astimezone(timezone.utc).isoformat()
    cutoff_30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # 30-day case + revenue trend via two aggregations bucketed by IST date string.
    # We bucket using a UTC->IST offset of +330 minutes then a $dateToString.
    ist_date_expr = {
        "$dateToString": {
            "format": "%Y-%m-%d",
            "date": {"$dateAdd": {
                "startDate": {"$dateFromString": {"dateString": "$created_at"}},
                "unit": "minute", "amount": 330,
            }},
        }
    }
    case_buckets = await db.cases.aggregate([
        {"$match": {"created_at": {"$gte": start_30, "$lt": end_30}}},
        {"$group": {"_id": ist_date_expr, "n": {"$sum": 1}}},
    ]).to_list(60)
    case_map = {b["_id"]: b["n"] for b in case_buckets if b["_id"]}

    rev_ist_date_expr = {
        "$dateToString": {
            "format": "%Y-%m-%d",
            "date": {"$dateAdd": {
                "startDate": {"$dateFromString": {"dateString": "$updated_at"}},
                "unit": "minute", "amount": 330,
            }},
        }
    }
    rev_buckets = await db.payments.aggregate([
        {"$match": {"updated_at": {"$gte": start_30, "$lt": end_30}, "payment_status": "PAID"}},
        {"$group": {"_id": rev_ist_date_expr, "total": {"$sum": "$amount_paid"}}},
    ]).to_list(60)
    rev_map = {b["_id"]: b["total"] for b in rev_buckets if b["_id"]}

    case_trend = []
    for i in range(29, -1, -1):
        day_ist = now_ist - timedelta(days=i)
        key = day_ist.strftime("%Y-%m-%d")
        case_trend.append({
            "date": key,
            "label": day_ist.strftime("%d %b"),
            "cases": case_map.get(key, 0),
            "revenue": rev_map.get(key, 0),
        })

    # Logins by role (last 30 days)
    login_pipeline = [
        {"$match": {"action": "LOGIN", "created_at": {"$gte": cutoff_30}}},
        {"$group": {"_id": "$actor_role", "count": {"$sum": 1}}},
    ]
    login_agg = await db.audit_logs.aggregate(login_pipeline).to_list(20)
    logins_by_role = {a["_id"]: a["count"] for a in login_agg if a["_id"]}

    # Top complaint terms — tokenize in aggregation and group/count in Mongo.
    STOP = {"with", "from", "have", "been", "pain", "patient", "this", "that",
            "since", "very", "having", "and", "the", "for", "has", "but",
            "are", "was", "were", "not", "she", "him", "her", "his"}
    complaint_pipeline = [
        {"$match": {"complaint_text": {"$exists": True, "$ne": ""}}},
        {"$project": {
            "_id": 0,
            "tokens": {"$split": [{"$toLower": "$complaint_text"}, " "]},
        }},
        {"$unwind": "$tokens"},
        {"$project": {
            # Strip surrounding punctuation
            "term": {"$trim": {"input": "$tokens", "chars": ".,;:()[]\"'!?-\t "}}
        }},
        {"$match": {
            "term": {"$nin": list(STOP)},
            "$expr": {"$gte": [{"$strLenCP": "$term"}, 4]},
        }},
        {"$group": {"_id": "$term", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_agg = await db.cases.aggregate(complaint_pipeline).to_list(10)
    top_complaints = [{"term": a["_id"], "count": a["count"]} for a in top_agg if a["_id"]]

    # Avg consultation-to-billing turnaround (minutes) for closed cases in last 30d.
    turnaround_pipeline = [
        {"$match": {
            "status": STATUS_CLOSED,
            "closed_at": {"$gte": cutoff_30},
            "consultation_started_at": {"$exists": True, "$ne": None},
        }},
        {"$project": {
            "_id": 0,
            "duration_min": {"$divide": [
                {"$subtract": [
                    {"$dateFromString": {"dateString": "$closed_at"}},
                    {"$dateFromString": {"dateString": "$consultation_started_at"}},
                ]},
                60000,
            ]},
        }},
        {"$group": {"_id": None, "avg": {"$avg": "$duration_min"}, "n": {"$sum": 1}}},
    ]
    t_agg = await db.cases.aggregate(turnaround_pipeline).to_list(1)
    avg_turnaround_min = round(t_agg[0]["avg"], 1) if t_agg and t_agg[0].get("avg") is not None else 0
    closed_cases_30d = t_agg[0]["n"] if t_agg else 0

    return {
        "case_trend_30d": case_trend,
        "logins_by_role_30d": logins_by_role,
        "top_complaints": top_complaints,
        "avg_turnaround_minutes": avg_turnaround_min,
        "closed_cases_30d": closed_cases_30d,
    }
