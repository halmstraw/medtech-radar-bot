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

SYSTEM_PROMPT = """You are an expert technology radar assistant for a Class IIa regulated medical device software platform.

The platform is built on:
- Azure (AKS, ACR, Azure ML, Azure Container Apps)
- GitHub Actions for CI/CD
- Python for ML/signal processing, Swift/Kotlin for mobile
- MLflow for experiment tracking
- Qualio for QMS, TestRail for test management

The radar has four quadrants:
- tools: CI/CD, testing, analysis, and development tooling
- platforms: Cloud, hosting, and infrastructure platforms
- languages-frameworks: Programming languages, application frameworks, and ML toolkits
- techniques: Engineering processes, governance models, and delivery practices

The radar has four rings:
- adopt: Decided and committed to — use with confidence
- trial: In active use but under evaluation — worth pursuing
- assess: Open decision or shortlisted — worth understanding
- hold: Explicitly rejected or being phased out — do not start

Current radar context (existing entries — avoid duplicates):
{radar_context}

When given a technology suggestion:
1. Research the technology if needed
2. Consider how it fits the platform context above
3. Recommend the most appropriate quadrant and ring
4. Write a concise 2-3 sentence description explaining the placement
5. Suggest relevant tags from: ci-cd, devops, cloud, ml, mobile, testing, compliance, security, infrastructure, framework, language, monitoring, observability, regulated, governance, process

Respond ONLY with a valid JSON object. No markdown fences, no preamble, no explanation — just the JSON:
{"title": "Technology Name", "quadrant": "tools", "ring": "assess", "tags": ["tag1", "tag2"], "reasoning": "One sentence.", "description": "2-3 sentences.", "entry_markdown": "---\\ntitle: \\"Technology Name\\"\\nring: assess\\nquadrant: tools\\ntags: [tag1, tag2]\\n---\\n\\n2-3 sentences."}"""


def research_and_recommend(suggestion: str, radar_context: str) -> dict[str, Any]:
    """Ask Claude to research a technology and recommend placement."""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = SYSTEM_PROMPT.format(radar_context=radar_context)

    logger.info("Calling Claude API for suggestion: %s", suggestion[:100])

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Suggest radar placement for: {suggestion}"
                },
                {
                    "role": "assistant",
                    "content": "{"
                }
            ],
        )
    except Exception as e:
        logger.error("Claude API call failed: %s", str(e))
        raise

    logger.info("Claude stop_reason: %s", response.stop_reason)

    # Extract text — we pre-filled the assistant turn with "{" so prepend it
    text_content = "{"
    for block in response.content:
        if hasattr(block, "text"):
            text_content += block.text

    logger.info("Claude raw: %s", repr(text_content[:400]))

    try:
        return json.loads(text_content)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s | raw: %s", e, repr(text_content[:400]))
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
