"""
Step 5: Full Pipeline - Merge Stage 1 + Stage 2 into Canonical Skill IDs
--------------------------------------------------------------------------
Ye file sab kuch jod ke ek single function deti hai jo Member 2 (backend)
call kar sakta hai: resume PDF do, wapas clean Skill IDs milte hain.

Golden Rule follow ho raha hai: sirf Skill IDs return hoti hain,
kabhi bhi raw text seedha database mein nahi jaata.
"""

from pdf_extractor import extract_text_from_pdf
from alias_matcher import load_registry, build_alias_map, stage1_match
from nlp_matcher import extract_candidate_phrases, stage2_match


def run_pipeline(pdf_path: str, registry_path: str) -> dict:
    registry = load_registry(registry_path)
    alias_map = build_alias_map(registry)

    text = extract_text_from_pdf(pdf_path)

    # Stage 1: fast alias lookup
    stage1_ids, stage1_phrases = stage1_match(text, alias_map)

    # Stage 2: NLP based matching on the full text
    candidates = extract_candidate_phrases(text)
    stage2_ids, unmatched = stage2_match(candidates, registry)

    final_skill_ids = stage1_ids | stage2_ids

    return {
        "status": "success",
        "data": {
            "skill_ids": sorted(final_skill_ids),
        },
        "unmatched_terms": unmatched,  # review karo, database mein mat daalo
        "errors": None,
    }


if __name__ == "__main__":
    # Test run: apne paas ek sample_resume.pdf rakho isi folder mein
    result = run_pipeline("m resume.pdf", "skills_registry_sample.json")
    print(result)
