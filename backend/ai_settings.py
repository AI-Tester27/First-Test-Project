"""AI provider settings."""

PROVIDERS = ("openai", "anthropic", "gemini")

KEY_FIELD = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

MODELS = {
    "openai": [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.2",
    ],
    "anthropic": [
        "claude-sonnet-4-5-20250929",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "gemini": [
        "gemini-2.5-pro",
        "gemini-3-flash-preview",
        "gemini-3.5-flash",
        "gemini-3.1-pro-preview",
    ],
}

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-5.5"


async def resolve_ai_config(db):
    doc = await db.settings.find_one({"_id": "ai"}) or {}

    provider = doc.get("AI_PROVIDER", DEFAULT_PROVIDER)

    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER

    model = doc.get("AI_MODEL", MODELS[provider][0])

    if model not in MODELS[provider]:
        model = MODELS[provider][0]

    api_key = (doc.get(KEY_FIELD[provider]) or "").strip()

    if not api_key:
        raise Exception(f"{provider} API key is not configured")

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "key_source": "own",
    }


async def ai_settings_summary(db):
    doc = await db.settings.find_one({"_id": "ai"}) or {}

    cfg = await resolve_ai_config(db)

    return {
        "active_provider": cfg["provider"],
        "active_model": cfg["model"],
        "key_source": cfg["key_source"],
        "keys_configured": {
            p: bool((doc.get(KEY_FIELD[p]) or "").strip())
            for p in PROVIDERS
        },
        "models": MODELS,
    }
