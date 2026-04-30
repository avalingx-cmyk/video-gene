BLOCKED_KEYWORDS = [
    "nsfw", "nude", "naked", "sex", "porn", "explicit",
    "gore", "violence", "hate", "self-harm",
]


def filter_content(prompt: str) -> tuple[bool, str | None]:
    """
    Check prompt against content safety filters.
    Returns (is_safe, reason_if_blocked).
    """
    prompt_lower = prompt.lower()

    for keyword in BLOCKED_KEYWORDS:
        if keyword in prompt_lower:
            return False, f"Blocked keyword: {keyword}"

    return True, None
