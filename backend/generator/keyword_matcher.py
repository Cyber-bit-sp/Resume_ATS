import re
from collections import Counter


STOPWORDS = {
    "and",
    "are",
    "but",
    "can",
    "for",
    "from",
    "have",
    "how",
    "into",
    "not",
    "our",
    "that",
    "the",
    "this",
    "with",
    "you",
    "your",
    "will",
    "its",
    "re",
    "we",
    "all",
    "any",
    "day",
    "end",
    "get",
    "has",
    "let",
    "new",
    "now",
    "one",
    "out",
    "way",
    "what",
    "when",
    "where",
    "who",
    "why",
    "about",
    "across",
    "already",
    "become",
    "beyond",
    "company",
    "companies",
    "culture",
    "daily",
    "every",
    "everyone",
    "first",
    "global",
    "hiring",
    "journey",
    "made",
    "more",
    "most",
    "much",
    "need",
    "needs",
    "only",
    "people",
    "person",
    "question",
    "right",
    "solely",
    "something",
    "speaks",
    "standard",
    "start",
    "stop",
    "today",
    "treating",
    "unique",
    "until",
    "wait",
    "we're",
    "works",
    "work",
    "team",
    "role",
    "using",
    "experience",
    "alan",
    "alaner",
    "alaners",
}


def extract_keywords(text, limit=30):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text or "")
    normalized = [word.strip(".,;:()[]{}").lower() for word in words]
    candidates = [word for word in normalized if len(word) > 2 and word not in STOPWORDS]
    counts = Counter(candidates)
    return [word for word, _ in counts.most_common(limit)]


def score_resume(job_description, generated_resume):
    job_keywords = extract_keywords(job_description)
    resume_text = (generated_resume or "").lower()
    matched = [keyword for keyword in job_keywords if keyword in resume_text]
    missing = [keyword for keyword in job_keywords if keyword not in resume_text]
    score = round((len(matched) / len(job_keywords)) * 100) if job_keywords else 0
    return {
        "score": score,
        "matched_keywords": matched,
        "missing_keywords": missing[:15],
    }
