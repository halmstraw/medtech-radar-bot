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

Respond ONLY with a JSON object in this exact format, no markdown fences, no preamble:
{
  "title": "Technology Name",
  "quadrant": "tools",
  "ring": "assess",
  "tags": ["tag1", "tag2"],
  "reasoning": "One sentence explaining why this quadrant and ring.",
  "description": "2-3 sentences for the radar entry body.",
  "entry_markdown": "---\\ntitle: \\"Technology Name\\"\\nring: assess\\nquadrant: tools\\ntags: [tag1, tag2]\\n---\\n\\n2-3 sentence description."
}"""


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
                    "content": f"Please research and recommend radar placement for: {suggestion}"
                }
            ],
        )
    except Exception as e:
        logger.error("Claude API call failed: %s", str(e))
        raise

    logger.info("Claude response stop_reason: %s", response.stop_reason)

    # Extract text content from response
    text_content = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_content += block.text

    logger.info("Claude raw response: %s", text_content[:500])

    if not text_content.strip():
        raise ValueError("Claude returned empty response")

    logger.info("Claude raw response: %s", text_content[:500])

    # Find the JSON object — extract everything between first { and last }
    start = text_content.find("{")
    end = text_content.rfind("}") + 1
    if start == -1 or end == 0:
        logger.error("No JSON object found in Claude response: %s", text_content[:500])
        raise ValueError("Claude response contained no JSON object")

    clean = text_content[start:end]

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude JSON: %s\nExtracted: %s", e, clean[:500])
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
