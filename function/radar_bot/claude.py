"""
claude.py — Anthropic API integration
Researches a technology and recommends quadrant/ring.
"""

import json
import logging
import os
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

# NOTE: Literal braces in the example JSON must be doubled ({{ }}) to avoid
# Python's str.format() treating them as template placeholders.
SYSTEM_PROMPT = """You are a technology radar assistant for a Class IIa regulated medical device software platform.

The platform uses: Azure (AKS, ACR, Azure ML), GitHub Actions, Python, Swift, Kotlin, MLflow, Qualio, TestRail.

Quadrants (use exact id strings):
- tools: CI/CD, testing, analysis, dev tooling
- platforms: cloud, hosting, infrastructure
- languages-frameworks: languages, frameworks, ML toolkits
- techniques: engineering processes, governance, delivery practices

Rings (use exact id strings):
- adopt: decided and in use
- trial: in active evaluation
- assess: shortlisted, worth understanding
- hold: rejected or phased out

Current radar entries (avoid duplicates):
{radar_context}

Respond with ONLY a single JSON object, no other text:
{{"title": "Name", "quadrant": "tools", "ring": "assess", "tags": ["tag1"], "reasoning": "One sentence.", "description": "2-3 sentences.", "entry_markdown": "---\\ntitle: \\"Name\\"\\nring: assess\\nquadrant: tools\\ntags: [tag1]\\n---\\n\\n2-3 sentences."}}"""


def research_and_recommend(suggestion: str, radar_context: str) -> dict[str, Any]:
    """Ask Claude to research a technology and recommend placement."""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = SYSTEM_PROMPT.format(radar_context=radar_context)

    logger.info("Calling Claude API for: %s", suggestion[:100])

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Suggest radar placement for: {suggestion}"
                }
            ],
        )
    except Exception as e:
        logger.error("Claude API call failed: %s", str(e))
        raise

    logger.info("Claude stop_reason: %s", response.stop_reason)

    text_content = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_content += block.text

    logger.info("Claude raw: %s", repr(text_content[:400]))

    # Extract JSON — find outermost { } regardless of preamble or fences
    start = text_content.find("{")
    end = text_content.rfind("}") + 1
    if start == -1 or end == 0:
        logger.error("No JSON found in response: %s", repr(text_content[:400]))
        raise ValueError("Claude response contained no JSON object")

    clean = text_content[start:end]

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s | extracted: %s", e, repr(clean[:400]))
        raise


def generate_entry(title: str, quadrant: str, ring: str, tags: list[str], description: str) -> str:
    """Generate the final .md file content for a radar entry."""
    tags_str = ", ".join(tags)
    return f"""---
title: "{title}"
ring: {ring}
quadrant: {quadrant}
tags: [{tags_str}]
---

{description}
"""
