"""AI provider settings: admin-managed keys with Emergent universal-key fallback."""
import os

PROVIDERS = ("anthropic", "openai", "gemini")

KEY_FIELD = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

# Models offered in the admin dropdown, per provider (first = default)
MODELS = {
    "anthropic": [
        "claude-sonnet-4-5-20250929",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "openai": [
        "gpt-5.4",
        "gpt-5.5",
        "gpt-5.4-mini",
        "gpt-5.2",
    ],
    "gemini": [
        "gemini-3.1-pro-preview",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
    ],
}

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


async def resolve_ai_config(db) -> dict:
    """Resolve active provider/model/key.
    Uses the admin-selected provider+model. Uses the admin's own key for that
    provider when stored; otherwise falls back to the built-in Emergent key.
    Returns {provider, model, api_key, key_source, fallback_key}.
    """
    doc = await db.settings.find_one({"_id": "ai"}) or {}
    provider = doc.get("AI_PROVIDER") or DEFAULT_PROVIDER
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER
    model = doc.get("AI_MODEL")
    if not model or model not in MODELS[provider]:
        model = MODELS[provider][0]
    own_key = (doc.get(KEY_FIELD[provider]) or "").strip()
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if own_key:
        return {
            "provider": provider, "model": model,
            "api_key": own_key, "key_source": "own",
            "fallback_key": emergent_key,
        }
    return {
        "provider": provider, "model": model,
        "api_key": emergent_key, "key_source": "emergent",
        "fallback_key": None,
    }


async def ai_settings_summary(db) -> dict:
    """Non-secret summary for the admin UI."""
    cfg = await resolve_ai_config(db)
    doc = await db.settings.find_one({"_id": "ai"}) or {}
    return {
        "active_provider": cfg["provider"],
        "active_model": cfg["model"],
        "key_source": cfg["key_source"],  # "own" | "emergent"
        "keys_configured": {p: bool((doc.get(KEY_FIELD[p]) or "").strip()) for p in PROVIDERS},
        "models": MODELS,
    }
