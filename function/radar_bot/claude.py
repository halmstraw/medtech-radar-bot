"""
claude.py — Anthropic API integration
Researches a technology and recommends quadrant/ring.
Uses web search tool with agentic loop for accurate results.
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

Use web search to research the technology before making your recommendation.
Then respond with ONLY a single JSON object, no other text:
{{"title": "Name", "quadrant": "tools", "ring": "assess", "tags": ["tag1"], "reasoning": "One sentence.", "description": "2-3 sentences.", "entry_markdown": "---\\ntitle: \\"Name\\"\\nring: assess\\nquadrant: tools\\ntags: [tag1]\\n---\\n\\n2-3 sentences."}}"""

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}
MAX_ITERATIONS = 5


def research_and_recommend(suggestion: str, radar_context: str) -> dict[str, Any]:
    """Ask Claude to research a technology and recommend placement.

    Uses an agentic loop to handle web search tool calls — Claude may search
    multiple times before producing the final JSON recommendation.
    """

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = SYSTEM_PROMPT.format(radar_context=radar_context)

    logger.info("Calling Claude API for: %s", suggestion[:100])

    messages = [
        {
            "role": "user",
            "content": f"Suggest radar placement for: {suggestion}"
        }
    ]

    iterations = 0
    while iterations < MAX_ITERATIONS:
        iterations += 1
        logger.info("Claude API call iteration %d", iterations)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=prompt,
                tools=[WEB_SEARCH_TOOL],
                messages=messages,
            )
        except Exception as e:
            logger.error("Claude API call failed: %s", str(e))
            raise

        logger.info("Claude stop_reason: %s (iteration %d)", response.stop_reason, iterations)

        if response.stop_reason == "end_turn":
            # Claude is done — extract JSON from the final text block
            text_content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_content += block.text

            logger.info("Claude final response: %s", repr(text_content[:400]))
            return _extract_json(text_content)

        elif response.stop_reason == "tool_use":
            # Claude wants to search — append its response and the tool results
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info("Claude searching for: %s", getattr(block, "input", {}))
                    # The web_search tool is server-side — results come back
                    # automatically in the next response via tool_result blocks
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search executed.",
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            logger.error("Unexpected stop_reason: %s", response.stop_reason)
            raise ValueError(f"Unexpected stop_reason: {response.stop_reason}")

    raise ValueError(f"Claude did not produce a final response after {MAX_ITERATIONS} iterations")


def _extract_json(text_content: str) -> dict[str, Any]:
    """Extract and parse the JSON object from Claude's response."""
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
