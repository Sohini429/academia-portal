"""
Step 4: Stage 2 - NLP Entity Recognition + Semantic Matching
---------------------------------------------------------------
Jo skills Stage 1 (alias lookup) miss kar gaya — jaise koi skill jo
different wording mein likhi hai — unke liye ye stage kaam aata hai.

1. spaCy se text ke "noun phrases" nikaalte hain (candidate skill terms).
2. Sentence-Transformers se un phrases ka embedding banate hain aur
   canonical skill names ke embeddings se compare (cosine similarity)
   karte hain. Jo sabse close match ho aur threshold cross kare,
   wahi accept hota hai.
"""

import spacy
from sentence_transformers import SentenceTransformer, util

# Ye dono models ek baar load hote hain (startup pe), baar baar nahi
nlp = spacy.load("en_core_web_sm")
embedder = SentenceTransformer("all-MiniLM-L6-v2")


def extract_candidate_phrases(text: str):
    """Text se possible skill-jaisi phrases nikaalo."""
    doc = nlp(text)
    phrases = set()
    for chunk in doc.noun_chunks:
        cleaned = chunk.text.strip()
        if 2 <= len(cleaned) <= 40:
            phrases.add(cleaned)
    return list(phrases)


def stage2_match(candidate_phrases, registry, threshold: float = 0.75):
    """Candidate phrases ko canonical skill names se semantically match karo.
    threshold jitna high hoga utna strict matching hoga (kam galat matches,
    lekin kuch sahi skills bhi miss ho sakti hain — is par tuning zaruri hai).
    """
    if not candidate_phrases:
        return set(), []

    canonical_names = [s["canonical_name"] for s in registry]
    canonical_ids = [s["id"] for s in registry]

    canonical_embeds = embedder.encode(canonical_names, convert_to_tensor=True)
    phrase_embeds = embedder.encode(candidate_phrases, convert_to_tensor=True)

    matched_ids = set()
    unmatched_phrases = []  # log karo, database mein mat daalo

    for i, phrase in enumerate(candidate_phrases):
        sims = util.cos_sim(phrase_embeds[i], canonical_embeds)[0]
        best_idx = int(sims.argmax())
        best_score = float(sims[best_idx])

        if best_score >= threshold:
            matched_ids.add(canonical_ids[best_idx])
        else:
            unmatched_phrases.append((phrase, round(best_score, 3)))

    return matched_ids, unmatched_phrases


if __name__ == "__main__":
    from alias_matcher import load_registry
    registry = load_registry("skills_registry_sample.json")
    sample_text = "Worked extensively on deep learning models and data pipelines."
    candidates = extract_candidate_phrases(sample_text)
    ids, unmatched = stage2_match(candidates, registry)
    print("Candidates:", candidates)
    print("Matched IDs:", ids)
    print("Unmatched (for review):", unmatched)
