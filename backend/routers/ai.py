"""AI assist endpoints: per-case, per-patient (recap), and notes parsing."""
import os
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

router = APIRouter()
log = logging.getLogger(__name__)


async def _call_llm(system: str, user_text: str, tag: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"ai-{tag}-{uuid.uuid4()}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    return await chat.send_message(UserMessage(text=user_text))


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
        system = (
            "You are a clinical documentation assistant for a homeopathy clinic. "
            "Produce a neutral structured draft with sections: Assessment Summary, Questions to Ask, Red Flags. "
            "Do NOT provide definitive diagnosis. Use 'may/possible' language. Keep concise (under 200 words)."
        )
        user_text = (
            f"Patient: Age {patient.get('age', '?')}, Gender: {patient.get('gender', '?')}\n"
            f"Known allergies: {(note or {}).get('sensitivity_allergies') or 'None reported'}\n"
            f"Complaint: {c['complaint_text']}"
        )
    elif action == "advice":
        lang_note = "Write the patient-facing advice in Telugu script." if lang == "TE" else "Write in clear English."
        system = (
            "You are writing patient-friendly follow-up advice for a homeopathy patient. "
            f"Avoid absolute claims. Use simple language. Do not add new medicines. {lang_note} Under 150 words."
        )
        med_list = ", ".join([(it.get("medicine_name") or "?") for it in (latest_p or {}).get("items", [])]) or "(none yet)"
        user_text = (
            f"Diagnosis: {(note or {}).get('diagnosis_summary') or c['complaint_text']}\n"
            f"Medicines: {med_list}\n"
            f"Follow-up date: {c.get('next_followup_at') or 'Not set'}"
        )
    else:  # instructions
        lang_note = "Write instructions in Telugu." if lang == "TE" else "Write in English."
        system = (
            "Convert prescription items into a clear, numbered patient instruction list. "
            f"Do not invent missing details. {lang_note} Be concise."
        )
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
    lines = [
        f"Patient: {patient.get('first_name', '')} {patient.get('last_name', '')}, "
        f"{patient.get('gender', '?')}, age {patient.get('age', '?')}. "
        f"UID: {patient.get('patient_uid', '')}. Total visits: {len(cases)}.",
        f"Height: {patient.get('height_cm') or '—'} cm, Weight: {patient.get('weight_kg') or '—'} kg, BMI: {bmi_str}.",
        f"Marital status: {patient.get('marital_status') or '—'}. Language: {patient.get('preferred_language') or 'EN'}.",
    ]
    for i, c in enumerate(cases, 1):
        when = c.get("created_at", "")[:10]
        note = await db.clinical_notes.find_one({"case_id": c["id"]}, {"_id": 0})
        rx = await db.prescriptions.find({"case_id": c["id"]}, {"_id": 0}).sort("version_no", -1).limit(1).to_list(1)
        med_list = ", ".join([(it.get("medicine_name") or "") + " " + (it.get("potency") or "")
                              for it in ((rx[0] if rx else {}).get("items") or [])]).strip(", ") or "—"
        lines.append(
            f"Visit {i} ({when}): Complaint: {c.get('complaint_text', '')[:200]}\n"
            f"  Diagnosis: {((note or {}).get('diagnosis_summary') or '—')[:200]}\n"
            f"  Allergies: {((note or {}).get('sensitivity_allergies') or '—')[:120]}\n"
            f"  Rx: {med_list[:240]}"
        )
    narrative = "\n".join(lines)

    lang = patient.get("preferred_language", "EN")
    if mode == "brief":
        lang_note = "Write briefing in clear English." if lang != "TE" else "Write briefing in clear English (NOT Telugu — for the doctor's quick scan)."
        system = (
            "You are a clinical assistant briefing a homeopathy doctor before they see a returning patient. "
            "Read the chronological visit history and produce EXACTLY 5 short bullet lines that help the doctor "
            "make the next decision quickly. Use this structure: "
            "(1) Pattern across visits, "
            "(2) What seemed to help, "
            "(3) What didn't help / red flags, "
            "(4) Allergies & cautions, "
            "(5) Suggested focus for today's consultation. "
            "Avoid definitive diagnosis. Use cautious 'may/possible' phrasing. "
            f"{lang_note} Keep every bullet under 20 words."
        )
    else:  # detailed
        system = (
            "You are a senior homeopathy clinical assistant preparing a comprehensive decision-support "
            "briefing for an experienced doctor. Read the full patient history below and produce a "
            "well-structured Markdown response with EXACTLY these sections, in this order:\n\n"
            "## 1. Patient Profile Summary\n"
            "A 2-3 sentence portrait covering demographics, build (BMI), and overall trajectory.\n\n"
            "## 2. Clinical Assessment\n"
            "Identify the recurring complaint patterns, time course, severity changes, and any concerning trends.\n\n"
            "## 3. Possible Diagnostic Directions\n"
            "List 2-4 possible diagnoses in order of likelihood, using cautious 'may suggest / possible' "
            "language. Briefly justify each from the history.\n\n"
            "## 4. Mother Tincture Suggestions\n"
            "Suggest 2-4 candidate homeopathic mother tinctures (Q potency) that align with the symptom "
            "picture and constitution, with a one-line rationale each. Use standard names "
            "(e.g. Belladonna Q, Bryonia Q). DO NOT prescribe dosage or duration — that is the doctor's call.\n\n"
            "## 5. Lifestyle Recommendations\n"
            "Three to five practical, India-context lifestyle/diet suggestions tailored to this patient.\n\n"
            "## 6. Treatment Considerations\n"
            "Highlight allergies, interactions to avoid, red flags warranting referral or labs, and follow-up cadence.\n\n"
            "## ⚠️ Disclaimer\n"
            "End with: 'This AI-generated analysis is decision-support only — for review by the treating doctor. "
            "Do not share with the patient without verification.'\n\n"
            "Style: concise, professional, use bullet lists inside each section. Total response should be "
            "around 350-500 words. Write in English."
        )

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

    system = (
        "You are a homeopathy clinic data-extraction assistant. The user pastes free-form "
        "doctor notes from Google Docs or a notebook. Extract a single visit's structured data. "
        "Output ONLY valid minified JSON (no prose, no markdown fences) with EXACTLY these keys:\n"
        '  {"visit_date": "YYYY-MM-DD" or null,\n'
        '   "complaint_text": str,\n'
        '   "diagnosis_summary": str,\n'
        '   "sensitivity_allergies": str,\n'
        '   "suggestions": str,\n'
        '   "additional_info": str,\n'
        '   "prescription_items": [{"medicine_name": str, "potency": str, "dosage": str,\n'
        '                           "frequency": str, "duration_days": int or null,\n'
        '                           "instructions": str}],\n'
        '   "notes_for_patient": str,\n'
        '   "consultation_amount": number or null,\n'
        '   "medicine_amount": number or null,\n'
        '   "amount_paid": number or null,\n'
        '   "payment_mode": "CASH"|"PHONEPE"|"CARD"|"OTHER"|null}\n'
        "Rules: (a) use empty string '' for missing strings, empty list for missing list, null for missing numbers/dates. "
        "(b) Do NOT invent medicines or diagnoses. Leave empty if unclear. "
        "(c) For potency normalize to formats like '30C', '200C', '1M', 'Q', '6X'. "
        "(d) For duration parse 'one week'=7, 'fortnight'=14, '10d'=10. "
        "(e) Currency symbols like ₹, Rs, rupees should be stripped. "
        "(f) Dates may appear as DD/MM/YYYY, DD-MM-YY, '14 Jan 2024' etc — output ISO YYYY-MM-DD."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"parse-{uuid.uuid4()}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        raw = await chat.send_message(UserMessage(text=text))
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
