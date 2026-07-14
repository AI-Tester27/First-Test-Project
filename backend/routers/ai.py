"""AI assist endpoints: per-case, per-patient (recap), and notes parsing."""
import json
import re
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException

from core import (
    db, audit,
    get_current_user, require_roles, load_case_for_user,
    ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_RECEPTION, ROLE_ADMIN,
)
from models import ParseNotesIn
import prompts

router = APIRouter()
log = logging.getLogger(__name__)


async def _call_llm(system: str, user_text: str, tag: str) -> str:
    """Call the configured AI provider. Uses the admin's own key when set;
    on failure (invalid/expired key) retries once with the built-in Emergent key."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from ai_settings import resolve_ai_config
    cfg = await resolve_ai_config(db)

    async def _run(key: str) -> str:
        chat = LlmChat(
            api_key=key,
            session_id=f"ai-{tag}-{uuid.uuid4()}",
            system_message=system,
        ).with_model(cfg["provider"], cfg["model"])
        return await chat.send_message(UserMessage(text=user_text))

    try:
        return await _run(cfg["api_key"])
    except Exception:
        if cfg["key_source"] == "own" and cfg["fallback_key"]:
            log.warning("Own %s key failed for %s; falling back to Emergent key", cfg["provider"], tag)
            return await _run(cfg["fallback_key"])
        raise


@router.post("/cases/{case_id}/ai/{action}")
async def ai_assist(
    case_id: str,
    action: str,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR)),
):
    if action not in ("summarize", "advice", "instructions"):
        raise HTTPException(status_code=400, detail="Invalid action")
    c = await load_case_for_user(case_id, user)
    patient = await db.patients.find_one({"id": c["patient_id"]}, {"_id": 0})
    note = await db.clinical_notes.find_one({"case_id": case_id}, {"_id": 0})
    latest = await db.prescriptions.find({"case_id": case_id}).sort("version_no", -1).limit(1).to_list(1)
    latest_p = latest[0] if latest else None
    lang = patient.get("preferred_language", "EN") if patient else "EN"

    if action == "summarize":
        system = prompts.case_summarize()
        user_text = (
            f"Patient: Age {patient.get('age', '?')}, Gender: {patient.get('gender', '?')}\n"
            f"Known allergies: {(note or {}).get('sensitivity_allergies') or 'None reported'}\n"
            f"Complaint: {c['complaint_text']}"
        )
    elif action == "advice":
        system = prompts.case_advice(lang)
        med_list = ", ".join([(it.get("medicine_name") or "?") for it in (latest_p or {}).get("items", [])]) or "(none yet)"
        user_text = (
            f"Diagnosis: {(note or {}).get('diagnosis_summary') or c['complaint_text']}\n"
            f"Medicines: {med_list}\n"
            f"Follow-up date: {c.get('next_followup_at') or 'Not set'}"
        )
    else:  # instructions
        system = prompts.case_instructions(lang)
        lines = []
        for it in (latest_p or {}).get("items", []):
            lines.append(
                f"- {it.get('medicine_name', '')} {it.get('potency', '')} — {it.get('dosage', '')} "
                f"{it.get('frequency', '')} for {it.get('duration_days') or '?'} days. {it.get('instructions', '')}"
            )
        user_text = "\n".join(lines) or "(no items)"

    try:
        result = await _call_llm(system, user_text, f"case-{action}")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("AI error")
        raise HTTPException(status_code=502, detail=f"AI service error: {e}") from e

    await audit(user, "AI_USED", "Case", case_id, {"action": action})
    return {"action": action, "result": result}


@router.post("/patients/{patient_id}/ai/recap")
async def ai_visit_recap(
    patient_id: str,
    mode: str = "brief",
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN)),
):
    """Generate a briefing of the patient's full visit history for the doctor.
    mode='brief' (default) → 5-line bullet briefing.
    mode='detailed' → comprehensive structured analysis (owner doctor / admin only)."""
    if mode not in ("brief", "detailed"):
        raise HTTPException(status_code=400, detail="mode must be 'brief' or 'detailed'")
    if mode == "detailed" and user["role"] not in (ROLE_OWNER_DOCTOR, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Detailed analysis is restricted to owner doctor / admin")

    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    q = {"patient_id": patient_id}
    if user["role"] == ROLE_DOCTOR:
        q["assigned_doctor_id"] = user.get("doctor_id")
    cases = await db.cases.find(q, {"_id": 0}).sort("created_at", 1).to_list(200)
    if not cases:
        raise HTTPException(status_code=404, detail="No accessible visits for this patient")

    # Build a compact, chronological narrative
    bmi_str = f"{patient.get('bmi')}" if patient.get('bmi') else "—"
    sources = ", ".join(patient.get("sources") or []) or "—"
    lines = [
        "=== PATIENT PROFILE ===",
        f"Name: {patient.get('first_name', '')} {patient.get('last_name', '')}",
        f"UID: {patient.get('patient_uid', '')}",
        f"Age: {patient.get('age', '?')} · Gender: {patient.get('gender', '?')} · Marital status: {patient.get('marital_status') or '—'}",
        f"Phone: {patient.get('phone', '—')} · Language: {patient.get('preferred_language') or 'EN'}",
        f"Address: {patient.get('address') or '—'}",
        f"Height: {patient.get('height_cm') or '—'} cm · Weight: {patient.get('weight_kg') or '—'} kg · BMI: {bmi_str}",
        f"Acquisition sources: {sources}",
        f"Referral name: {patient.get('referral_name') or '—'}",
        f"Total visits on record: {len(cases)}",
        "",
        "=== VISIT HISTORY (chronological) ===",
    ]
    for i, c in enumerate(cases, 1):
        when = c.get("created_at", "")[:10]
        note = await db.clinical_notes.find_one({"case_id": c["id"]}, {"_id": 0}) or {}
        rx = await db.prescriptions.find({"case_id": c["id"]}, {"_id": 0}).sort("version_no", -1).limit(1).to_list(1)
        med_list = ", ".join([
            f"{it.get('medicine_name', '')} {it.get('potency', '')} {it.get('dosage', '')} {it.get('frequency', '')}".strip()
            for it in ((rx[0] if rx else {}).get("items") or [])
        ]).strip(", ") or "—"
        lines.append(
            f"Visit {i} — {when} · type {c.get('visit_type') or '—'} · status {c.get('status') or '—'}\n"
            f"  Complaint: {(c.get('complaint_text') or '—')[:300]}\n"
            f"  Diagnosis summary: {((note.get('diagnosis_summary')) or '—')[:300]}\n"
            f"  Allergies / sensitivity: {((note.get('sensitivity_allergies')) or '—')[:200]}\n"
            f"  Doctor's suggestions: {((note.get('suggestions')) or '—')[:200]}\n"
            f"  Additional notes: {((note.get('additional_info')) or '—')[:200]}\n"
            f"  Rx given: {med_list[:300]}\n"
            f"  Follow-up date set: {c.get('next_followup_date') or '—'}"
        )
    narrative = "\n".join(lines)

    lang = patient.get("preferred_language", "EN")
    if mode == "brief":
        system = prompts.recap_brief(lang)
    else:  # detailed — Master Prompt
        system = prompts.recap_master_prompt()

    try:
        result = await _call_llm(system, narrative, f"recap-{mode}-{patient_id}")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("AI recap error")
        raise HTTPException(status_code=502, detail=f"AI service error: {e}") from e

    await audit(user, "AI_USED", "Patient", patient_id, {"action": "recap", "mode": mode, "visits": len(cases)})
    return {"result": result, "visits_analysed": len(cases), "mode": mode}


@router.post("/ai/parse-visit-notes")
async def parse_visit_notes(
    payload: ParseNotesIn,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_RECEPTION, ROLE_ADMIN)),
):
    """Parse free-form clinical notes (e.g. pasted from Google Docs) into a structured
    historical-visit draft. Doctor reviews the draft before saving.
    """
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > 8000:
        raise HTTPException(status_code=413, detail="Notes too long (max 8000 chars)")

    system = prompts.parse_visit_notes()

    try:
        raw = await _call_llm(system, text, "parse-notes")
    except Exception as e:
        log.exception("Notes parse error")
        raise HTTPException(status_code=502, detail=f"AI service error: {e}") from e

    # Strip any accidental code fences and find the JSON object
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise HTTPException(status_code=502, detail="AI returned no JSON object")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}") from e

    # Light normalization / defaults
    parsed.setdefault("prescription_items", [])
    for k in ("complaint_text", "diagnosis_summary", "sensitivity_allergies",
              "suggestions", "additional_info", "notes_for_patient"):
        parsed.setdefault(k, "")

    await audit(user, "AI_USED", "Notes", "parse", {"chars": len(text), "items": len(parsed.get("prescription_items", []))})
    return {"draft": parsed, "raw": raw}
