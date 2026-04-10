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
1. Use web search to research the technology if needed
2. Consider how it fits the platform context above
3. Recommend the most appropriate quadrant and ring
4. Write a concise 2-3 sentence description explaining the placement
5. Suggest relevant tags from: ci-cd, devops, cloud, ml, mobile, testing, compliance, security, infrastructure, framework, language, monitoring, observability, regulated, governance, process

Respond ONLY with a JSON object in this exact format:
{{
  "title": "Technology Name",
  "quadrant": "tools|platforms|languages-frameworks|techniques",
  "ring": "adopt|trial|assess|hold",
  "tags": ["tag1", "tag2"],
  "reasoning": "One sentence explaining why this quadrant and ring.",
  "description": "2-3 sentences for the radar entry body. Reference relevant architectural decisions where applicable.",
  "entry_markdown": "---\\ntitle: \\"Technology Name\\"\\nring: adopt\\nquadrant: tools\\ntags: [tag1, tag2]\\n---\\n\\n2-3 sentence description."
}}"""


def research_and_recommend(suggestion: str, radar_context: str) -> dict[str, Any]:
    """Ask Claude to research a technology and recommend placement."""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = SYSTEM_PROMPT.format(radar_context=radar_context)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=prompt,
        messages=[
            {
                "role": "user",
                "content": f"Please research and recommend radar placement for: {suggestion}"
            }
        ],
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    # Extract text content from response
    text_content = ""
    for block in response.content:
        if block.type == "text":
            text_content += block.text

    # Parse JSON response
    # Strip markdown fences if present
    clean = text_content.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    return json.loads(clean)


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
