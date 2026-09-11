"""
Step 3: Stage 1 - Fast Regex & Alias Lookup
--------------------------------------------
Ye sabse tez wala stage hai. Ye har known skill aur uske common
shorthand/aliases (jaise 'py', 'python3') ko directly text mein dhoondta hai.
Ye 60-70% skills yahin pakad leta hai, NLP ki zarurat padne se pehle.
"""

import json
import re


def load_registry(path: str):
    """Load the master skill registry (from Member 2's DB export/JSON)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_alias_map(registry):
    """Build a lowercase alias -> skill_id lookup dict.
    Canonical name khud bhi ek alias ki tarah treat hota hai."""
    alias_map = {}
    for skill in registry:
        alias_map[skill["canonical_name"].lower()] = skill["id"]
        for alias in skill.get("aliases", []):
            alias_map[alias.lower()] = skill["id"]
    return alias_map


def stage1_match(text: str, alias_map: dict):
    """Text ke andar known aliases dhoondo.
    Returns: (matched_skill_ids set, matched_raw_phrases list)"""
    text_lower = text.lower()
    matched_ids = set()
    matched_phrases = []

    for alias, skill_id in alias_map.items():
        # \b use kiya hai taaki "java" "javascript" ke andar match na ho
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text_lower):
            matched_ids.add(skill_id)
            matched_phrases.append(alias)

    return matched_ids, matched_phrases


if __name__ == "__main__":
    registry = load_registry("skills_registry_sample.json")
    alias_map = build_alias_map(registry)
    sample_text = "Experienced in Python3, SQL queries and React for frontend."
    ids, phrases = stage1_match(sample_text, alias_map)
    print("Matched IDs:", ids)
    print("Matched phrases:", phrases)
