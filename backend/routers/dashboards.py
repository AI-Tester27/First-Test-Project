"""Role-specific dashboard endpoints: pharmacy, pro, admin-analytics."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends

from core import (
    db, now_utc, require_roles,
    ROLE_PHARMACY, ROLE_OWNER_DOCTOR, ROLE_ADMIN, ROLE_PRO,
    STATUS_CLOSED, STATUS_AWAITING_PRO, STATUS_SENT_PHARMACY, STATUS_IN_PHARMACY,
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
        "status": {"$in": [STATUS_AWAITING_PRO, STATUS_READY_BILLING, STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID]}
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
            # PRO viewers see patient name, ID, phone, scheduled date — NO clinical notes.
            followup_items.append({
                "id": r.get("id"),
                "patient_name": r.get("patient_name"),
                "patient_uid": r.get("patient_uid"),
                "patient_phone": r.get("patient_phone"),
                "scheduled_at": r.get("scheduled_at"),
                "scheduled_date": r.get("scheduled_date"),
                "status": r.get("status"),
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



@router.get("/pro/analytics")
async def pro_analytics(user: dict = Depends(require_roles(ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_ADMIN))):
    """Comprehensive business analytics for the PRO/Owner."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0)
    start_today, end_today = _today_bounds_utc()
    start_7d = (now_ist - timedelta(days=7)).astimezone(timezone.utc).isoformat()
    start_30d = (now_ist - timedelta(days=30)).astimezone(timezone.utc).isoformat()

    # ── PATIENT METRICS ──────────────────────────────────────────────────
    total_patients = await db.patients.count_documents({})
    new_today = await db.patients.count_documents({"created_at": {"$gte": start_today, "$lt": end_today}})
    new_7d = await db.patients.count_documents({"created_at": {"$gte": start_7d}})
    new_30d = await db.patients.count_documents({"created_at": {"$gte": start_30d}})
    by_gender_agg = await db.patients.aggregate([
        {"$group": {"_id": "$gender", "count": {"$sum": 1}}},
    ]).to_list(10)
    by_gender = {a["_id"]: a["count"] for a in by_gender_agg if a.get("_id")}

    age_buckets = await db.patients.aggregate([
        {"$bucket": {
            "groupBy": "$age",
            "boundaries": [0, 13, 25, 45, 60, 150],
            "default": "Unknown",
            "output": {"count": {"$sum": 1}},
        }},
    ]).to_list(10)
    labels = ["0-12", "13-24", "25-44", "45-59", "60+"]
    age_groups = {label: 0 for label in labels}
    for b in age_buckets:
        boundary = b.get("_id")
        if boundary == 0:
            age_groups["0-12"] = b["count"]
        elif boundary == 13:
            age_groups["13-24"] = b["count"]
        elif boundary == 25:
            age_groups["25-44"] = b["count"]
        elif boundary == 45:
            age_groups["45-59"] = b["count"]
        elif boundary == 60:
            age_groups["60+"] = b["count"]

    src_agg = await db.patients.aggregate([
        {"$match": {"created_at": {"$gte": start_30d}}},
        {"$unwind": {"path": "$sources", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$sources", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]).to_list(20)
    sources_30d = [{"source": a["_id"], "count": a["count"]} for a in src_agg]

    # ── VISIT METRICS ────────────────────────────────────────────────────
    total_visits = await db.cases.count_documents({})
    visits_today = await db.cases.count_documents({"created_at": {"$gte": start_today, "$lt": end_today}})
    visits_7d = await db.cases.count_documents({"created_at": {"$gte": start_7d}})
    visits_30d = await db.cases.count_documents({"created_at": {"$gte": start_30d}})
    by_visit_type_agg = await db.cases.aggregate([
        {"$match": {"created_at": {"$gte": start_30d}}},
        {"$group": {"_id": "$visit_type", "count": {"$sum": 1}}},
    ]).to_list(5)
    by_visit_type = {(a["_id"] or "UNKNOWN"): a["count"] for a in by_visit_type_agg}

    by_doctor_agg = await db.cases.aggregate([
        {"$match": {"created_at": {"$gte": start_30d}}},
        {"$group": {"_id": "$assigned_doctor_id", "count": {"$sum": 1}}},
    ]).to_list(10)
    docs_list = await db.doctor_profiles.find({}).to_list(50)
    docs_map = {d["id"]: d.get("display_name", d["id"]) for d in docs_list}
    cases_by_doctor_30d = [{"doctor": docs_map.get(b["_id"], b["_id"] or "Unassigned"), "count": b["count"]} for b in by_doctor_agg]

    # ── REVENUE METRICS ──────────────────────────────────────────────────
    revenue_total_agg = await db.payments.aggregate([
        {"$match": {"payment_status": "PAID"}},
        {"$group": {"_id": None, "billed": {"$sum": "$total_amount"}, "paid": {"$sum": "$amount_paid"}}},
    ]).to_list(1)
    rev_total = revenue_total_agg[0] if revenue_total_agg else {"billed": 0, "paid": 0}

    revenue_today_agg = await db.payments.aggregate([
        {"$match": {"updated_at": {"$gte": start_today, "$lt": end_today}, "payment_status": "PAID"}},
        {"$group": {"_id": None, "amount": {"$sum": "$amount_paid"}}},
    ]).to_list(1)
    revenue_today = revenue_today_agg[0]["amount"] if revenue_today_agg else 0

    revenue_30d_agg = await db.payments.aggregate([
        {"$match": {"updated_at": {"$gte": start_30d}, "payment_status": "PAID"}},
        {"$group": {"_id": None, "amount": {"$sum": "$amount_paid"}}},
    ]).to_list(1)
    revenue_30d = revenue_30d_agg[0]["amount"] if revenue_30d_agg else 0

    by_mode_30d = await db.payments.aggregate([
        {"$match": {"updated_at": {"$gte": start_30d}, "payment_status": {"$in": ["PAID", "PARTIAL"]}}},
        {"$group": {"_id": "$payment_mode", "amount": {"$sum": "$amount_paid"}, "n": {"$sum": 1}}},
    ]).to_list(10)
    mode_breakdown = [{"mode": a["_id"] or "UNKNOWN", "amount": a["amount"], "count": a["n"]} for a in by_mode_30d]

    consult_med_split = await db.payments.aggregate([
        {"$match": {"payment_status": {"$in": ["PAID", "PARTIAL"]}, "updated_at": {"$gte": start_30d}}},
        {"$group": {"_id": None,
                    "consultation": {"$sum": "$consultation_amount"},
                    "medicine": {"$sum": "$medicine_amount"}}},
    ]).to_list(1)
    cm_split = consult_med_split[0] if consult_med_split else {"consultation": 0, "medicine": 0}

    revenue_trend_pipeline = [
        {"$match": {"updated_at": {"$gte": start_30d}, "payment_status": "PAID"}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$dateAdd": {
                "startDate": {"$dateFromString": {"dateString": "$updated_at"}},
                "unit": "minute", "amount": 330,
            }}}},
            "amount": {"$sum": "$amount_paid"},
        }},
    ]
    rev_buckets = await db.payments.aggregate(revenue_trend_pipeline).to_list(60)
    rev_map = {b["_id"]: b["amount"] for b in rev_buckets if b["_id"]}
    revenue_trend_30d = []
    for i in range(29, -1, -1):
        day = now_ist - timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        revenue_trend_30d.append({"date": key, "label": day.strftime("%d %b"), "amount": rev_map.get(key, 0)})

    # ── OPERATIONAL METRICS ──────────────────────────────────────────────
    turnaround_pipeline = [
        {"$match": {
            "status": STATUS_CLOSED,
            "closed_at": {"$gte": start_30d},
            "consultation_started_at": {"$exists": True, "$ne": None},
        }},
        {"$project": {"_id": 0, "duration_min": {"$divide": [
            {"$subtract": [
                {"$dateFromString": {"dateString": "$closed_at"}},
                {"$dateFromString": {"dateString": "$consultation_started_at"}},
            ]},
            60000,
        ]}}},
        {"$group": {"_id": None, "avg": {"$avg": "$duration_min"}, "n": {"$sum": 1}}},
    ]
    t_agg = await db.cases.aggregate(turnaround_pipeline).to_list(1)
    avg_turnaround_min = round(t_agg[0]["avg"], 1) if t_agg and t_agg[0].get("avg") is not None else 0
    closed_30d = t_agg[0]["n"] if t_agg else 0

    # ── FINANCIAL METRICS ────────────────────────────────────────────────
    outstanding_agg = await db.payments.aggregate([
        {"$match": {"balance_amount": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$balance_amount"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    outstanding = outstanding_agg[0] if outstanding_agg else {"total": 0, "n": 0}

    return {
        "patient_metrics": {
            "total": total_patients,
            "new_today": new_today,
            "new_7d": new_7d,
            "new_30d": new_30d,
            "by_gender": by_gender,
            "by_age_group": age_groups,
            "age_group_order": labels,
            "sources_30d": sources_30d,
        },
        "visit_metrics": {
            "total": total_visits,
            "today": visits_today,
            "last_7d": visits_7d,
            "last_30d": visits_30d,
            "by_visit_type_30d": by_visit_type,
            "by_doctor_30d": cases_by_doctor_30d,
        },
        "revenue_metrics": {
            "total_billed": rev_total["billed"],
            "total_paid": rev_total["paid"],
            "today": revenue_today,
            "last_30d": revenue_30d,
            "by_mode_30d": mode_breakdown,
            "consult_vs_medicine_30d": {
                "consultation": cm_split.get("consultation", 0),
                "medicine": cm_split.get("medicine", 0),
            },
            "trend_30d": revenue_trend_30d,
        },
        "operational_metrics": {
            "avg_turnaround_minutes": avg_turnaround_min,
            "closed_cases_30d": closed_30d,
        },
        "financial_metrics": {
            "outstanding_amount": outstanding["total"],
            "outstanding_count": outstanding["n"],
        },
    }
