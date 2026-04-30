STYLE_DESCRIPTORS = {
    "educational": {
        "camera": "steady, clear framing, gentle zoom-ins for emphasis",
        "lighting": "bright, even, natural light",
        "pacing": "measured, with pauses for comprehension",
        "tone": "informative, approachable",
    },
    "marketing": {
        "camera": "dynamic angles, smooth tracking shots, dramatic reveals",
        "lighting": "studio-quality, high contrast, warm highlights",
        "pacing": "fast-paced, energetic cuts",
        "tone": "compelling, aspirational",
    },
    "technology": {
        "camera": "clean product shots, macro details, smooth pans",
        "lighting": "cool tones, rim lighting, futuristic ambiance",
        "pacing": "deliberate, showcasing details",
        "tone": "modern, precise, innovative",
    },
}


def enhance_prompt(prompt: str, style: str = "educational") -> str:
    """
    Enrich a user prompt with style-specific descriptors for better video generation.
    """
    descriptors = STYLE_DESCRIPTORS.get(style, STYLE_DESCRIPTORS["educational"])

    enhancement = (
        f"\n\nStyle: {style.capitalize()} video. "
        f"Camera: {descriptors['camera']}. "
        f"Lighting: {descriptors['lighting']}. "
        f"Pacing: {descriptors['pacing']}. "
        f"Tone: {descriptors['tone']}. "
        f"Aspect ratio: 9:16 (1080x1920 portrait)."
    )

    return prompt + enhancement
