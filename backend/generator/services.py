import json
import logging
import os
import re

from .keyword_matcher import extract_keywords, score_resume
from .prompts import SYSTEM_PROMPT, build_prompt


logger = logging.getLogger(__name__)


SECTION_KEYS = [
    "full_name",
    "contact_info",
    "professional_summary",
    "technical_skills",
    "professional_experience",
    "projects",
    "education",
    "certifications",
]

RESUME_RESPONSE_SCHEMA = {
    "name": "generated_resume_sections",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            key: {
                "type": "string",
                "description": "Plain text section content. Use newline-separated bullets where appropriate.",
            }
            for key in SECTION_KEYS
        },
        "required": SECTION_KEYS,
    },
    "strict": True,
}

DEFAULT_OPENAI_REFINEMENT_MIN_SCORE = 90

NOISY_KEYWORDS = {
    "they",
    "them",
    "their",
    "our",
    "ours",
    "about",
    "across",
    "within",
    "including",
    "preferred",
    "required",
    "responsibilities",
    "responsibility",
    "candidate",
    "position",
    "company",
    "customer",
    "customers",
    "people",
    "who",
    "support",
    "siena",
}

TECH_HINTS = {
    "python",
    "django",
    "flask",
    "react",
    "javascript",
    "typescript",
    "node",
    "postgresql",
    "mysql",
    "sqlite",
    "api",
    "rest",
    "graphql",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "redis",
    "llm",
    "llms",
    "ai-native",
    "agentic",
    "agents",
    "retrieval",
    "iam",
    "pam",
    "celery",
    "git",
    "linux",
    "html",
    "css",
    "ci",
    "cd",
}

GENERAL_PRO_SKILLS = {
    "backend",
    "frontend",
    "full",
    "stack",
    "architecture",
    "scalable",
    "performance",
    "security",
    "testing",
    "automation",
    "integration",
    "infrastructure",
    "workflows",
    "engineering",
    "design",
    "apis",
    "software",
    "internal",
    "tools",
    "organizational",
    "structured",
    "knowledge",
    "context",
    "user",
    "insurance",
    "prevention",
    "production",
    "system",
    "systems",
    "cloud",
    "database",
    "databases",
}

EXPERIENCE_HEADER_PATTERN = re.compile(
    r"(\||\b(19|20)\d{2}\b|present|current|\d{1,2}/\d{4}|\d{4}\s*[-–]\s*(present|current|\d{4}))",
    re.IGNORECASE,
)

PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d|phone\s*:)", re.IGNORECASE)


def _normalize_whitespace(value):
    lines = []
    for raw in (value or "").splitlines():
        cleaned = re.sub(r"[ \t]+", " ", raw).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines).strip()


def _normalize_bullet_lines(value):
    normalized = _normalize_whitespace(value)
    if not normalized:
        return ""
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if any(line.startswith("-") for line in lines):
        return "\n".join(line if line.startswith("-") else f"- {line}" for line in lines)
    return "\n".join(f"- {line}" for line in lines)


def _looks_like_experience_header(line):
    stripped = (line or "").strip().lstrip("-• ").strip()
    return bool(stripped and EXPERIENCE_HEADER_PATTERN.search(stripped))


def _normalize_experience_lines(value):
    normalized = _normalize_whitespace(value)
    if not normalized:
        return ""
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    output = []
    for line in lines:
        cleaned = line.lstrip("-• ").strip()
        if _looks_like_experience_header(cleaned):
            output.append(cleaned)
        else:
            output.append(cleaned if cleaned.startswith("-") else f"- {cleaned}")
    return "\n".join(output)


def _priority_keywords(text, limit=10):
    raw = extract_keywords(text, limit=40)
    cleaned = [k for k in raw if k not in NOISY_KEYWORDS and len(k) > 2]
    preferred = [
        k
        for k in cleaned
        if (k in TECH_HINTS)
        or (k in GENERAL_PRO_SKILLS)
        or any(ch in k for ch in ["+", "#", "."])
        or k.isupper()
    ]
    if preferred:
        return preferred[:limit]
    return cleaned[:limit]


def _extract_name(resume_text):
    for line in (resume_text or "").splitlines():
        line = line.strip()
        if line and len(line.split()) <= 5 and not any(char.isdigit() for char in line):
            return line
    return "Candidate Name"


def _extract_contact(resume_text):
    lines = []
    for line in (resume_text or "").splitlines()[:12]:
        lowered = line.lower()
        if any(token in lowered for token in ["@", "linkedin", "github", "http"]) or PHONE_PATTERN.search(line):
            lines.append(line.strip())
    return " | ".join(lines) if lines else "Email | Phone | Location | LinkedIn"


def build_automatic_job_description(resume_text, prompt_text):
    prompt_text = (prompt_text or "").strip()
    resume_text = (resume_text or "").strip()
    prompt_hint = prompt_text.splitlines()[0] if prompt_text else ""
    resume_hint = ""
    for line in resume_text.splitlines():
        if line.strip():
            resume_hint = line.strip()
            break

    inferred_keywords = []
    for keyword in ["python", "django", "react", "api", "postgresql", "docker", "aws", "llm", "agents", "backend", "frontend"]:
        if keyword.lower() in (prompt_text + " " + resume_text).lower():
            inferred_keywords.append(keyword)

    keywords_text = ", ".join(inferred_keywords[:6]) if inferred_keywords else "software engineering"
    title = "Generated Role"
    description = (
        f"Target a {keywords_text} role that emphasizes strong execution, clear communication, and impact. "
        f"{prompt_hint or 'Use the selected resume and prompt to tailor the output for this role.'}"
    )
    if resume_hint:
        description = f"{description} Base the content on the resume context: {resume_hint}."

    return {
        "job_title": title,
        "company_name": "Generated Company",
        "description_text": description,
        "job_url": "",
        "location": "",
        "work_type": "",
    }


SKILL_CATEGORIES = [
    ("Frontend", ("react", "typescript", "javascript", "react native", "html5", "html", "css3", "css", "redux", "angular", "vue")),
    ("Backend", ("node.js", "node", "python", "django", "fastapi", "flask", "express.js", "express", "rest api", "rest apis", "graphql", "api", "apis", "java", "spring", ".net", "c#")),
    ("Cloud & Infrastructure", ("aws", "amazon web services", "gcp", "google cloud", "azure", "docker", "kubernetes", "terraform", "ci/cd", "ci", "cd", "linux")),
    ("Databases & Caching", ("postgresql", "postgres", "redis", "mongodb", "mysql", "sqlite", "sql server", "oracle", "database", "databases", "caching")),
    ("Architecture & Systems", ("microservices", "distributed systems", "system design", "api-driven", "event-driven", "cloud-native", "scalable", "high availability", "fault tolerance", "architecture", "systems", "security")),
    ("AI & Automation", ("ai-native", "llms", "agents", "agentic", "internal tools", "workflows", "automation", "retrieval", "structured", "knowledge", "context", "organizational", "ai", "llm")),
    ("Domain & Integrations", ("open banking", "payment", "payments", "fintech", "banking", "financial", "healthcare", "insurance", "prevention", "integration", "integrations", "iam", "pam")),
    ("Tools & Collaboration", ("git", "agile", "scrum", "testing", "deployment", "monitoring", "production support", "observability", "code reviews", "collaboration")),
    ("Leadership", ("leadership", "mentoring", "technical mentoring", "team leadership", "cross-functional", "ownership")),
]

JOB_SKILL_ALIASES = {
    "modern web technologies": ("react", "typescript", "javascript", "html5", "css3"),
    "frontend": ("react", "typescript", "javascript", "html5", "css3"),
    "front-end": ("react", "typescript", "javascript", "html5", "css3"),
    "full-stack": ("react", "typescript", "javascript", "python", "api", "postgresql"),
    "fullstack": ("react", "typescript", "javascript", "python", "api", "postgresql"),
    "backend": ("python", "api", "apis", "postgresql", "system design"),
    "back-end": ("python", "api", "apis", "postgresql", "system design"),
    "oop languages": ("python", "java", "c#"),
    "llm apis": ("llms", "api", "apis"),
    "internal ai infrastructure": ("ai", "llms", "internal tools", "automation"),
    "internal platform": ("internal tools", "react", "python", "postgresql"),
    "internal tools": ("internal tools", "react", "python", "postgresql"),
    "intelligent agents": ("agents", "agentic", "ai", "automation"),
    "agentic assistants": ("agents", "agentic", "ai", "automation"),
    "structured outputs": ("structured", "llms"),
    "structured reasoning": ("structured", "llms"),
    "tool use": ("agents", "llms", "automation"),
    "human-in-the-loop": ("agents", "automation"),
    "knowledge retrieval": ("knowledge", "retrieval"),
    "organizational workflows": ("organizational", "workflows", "automation"),
    "identity & access management": ("iam", "security"),
    "identity and access management": ("iam", "security"),
    "privileged access management": ("pam", "security"),
    "user lifecycle": ("iam", "security", "systems"),
    "right abstractions": ("system design", "architecture"),
    "abstractions": ("system design", "architecture"),
    "production": ("production support", "monitoring"),
}


SKILL_DISPLAY = {
    "amazon web services": "Amazon Web Services (AWS)",
    "aws": "Amazon Web Services (AWS)",
    "gcp": "Google Cloud Platform (GCP)",
    "google cloud": "Google Cloud Platform (GCP)",
    "node": "Node.js",
    "node.js": "Node.js",
    "express": "Express.js",
    "express.js": "Express.js",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "api": "APIs",
    "apis": "APIs",
    "graphql": "GraphQL APIs",
    "react": "React.js",
    "react native": "React Native",
    "javascript": "JavaScript (ES6+)",
    "typescript": "TypeScript",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    "python": "Python",
    "django": "Django",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "redis": "Redis",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "database": "Database Systems",
    "databases": "Database Systems",
    "caching": "Caching",
    "ci": "CI/CD Pipelines",
    "cd": "CI/CD Pipelines",
    "ci/cd": "CI/CD Pipelines",
    "microservices": "Microservices Architecture",
    "api-driven": "API-Driven Development",
    "event-driven": "Event-Driven Systems",
    "cloud-native": "Cloud-Native Applications",
    "distributed systems": "Distributed Systems",
    "system design": "System Design",
    "scalable": "Scalable Systems",
    "architecture": "Software Architecture",
    "systems": "Distributed Systems",
    "ai": "AI",
    "ai-native": "AI-native Systems",
    "llm": "LLMs",
    "llms": "LLMs",
    "agentic": "Agentic Systems",
    "agents": "AI Agents",
    "retrieval": "Retrieval Systems",
    "automation": "Automation",
    "structured": "Structured Reasoning",
    "knowledge": "Knowledge Retrieval",
    "context": "Context Retrieval",
    "internal tools": "Internal Tools",
    "security": "Security",
    "workflows": "Workflow Automation",
    "organizational": "Organizational Workflows",
    "open banking": "Open Banking Integrations",
    "payment": "Payment Processing Systems",
    "payments": "Payment Processing Systems",
    "fintech": "FinTech",
    "banking": "Banking APIs",
    "financial": "Financial Transaction Workflows",
    "healthcare": "Healthcare Systems",
    "insurance": "Insurance Platforms",
    "prevention": "Prevention Workflows",
    "integration": "Integrations",
    "integrations": "Integrations",
    "iam": "Identity & Access Management (IAM)",
    "pam": "Privileged Access Management (PAM)",
    "git": "Git",
    "agile": "Agile/Scrum",
    "scrum": "Agile/Scrum",
    "testing": "Testing & Deployment Workflows",
    "deployment": "Testing & Deployment Workflows",
    "monitoring": "Monitoring & Production Support",
    "production support": "Monitoring & Production Support",
    "mentoring": "Technical Mentoring",
    "technical mentoring": "Technical Mentoring",
    "code reviews": "Code Reviews",
    "team leadership": "Small Team Leadership",
    "cross-functional": "Cross-Functional Collaboration",
    "leadership": "Technical Leadership",
    "collaboration": "Cross-Functional Collaboration",
}


def _skill_display(term):
    normalized = term.strip().lower()
    if normalized in SKILL_DISPLAY:
        return SKILL_DISPLAY[normalized]
    return _keyword_display(normalized)


def _extract_existing_skill_lines(text):
    skill_text = _extract_section_by_headings(
        text,
        {"skills", "technical skills", "core skills", "key skills", "technologies", "tech stack"},
        _experience_start_headings() | _experience_stop_headings() | {"summary", "professional summary"},
    )
    lines = []
    for line in skill_text.splitlines():
        cleaned = _clean_resume_line(line)
        if cleaned and ":" in cleaned:
            lines.append(cleaned)
    return lines


def _term_in_text(term, text):
    term = term.strip().lower()
    if not term:
        return False
    if any(ch in term for ch in ".+#/&-"):
        return term in text
    return bool(re.search(rf"\b{re.escape(term)}\b", text))


def _skill_relevant_to_job(term, job_text):
    if term in {"leadership", "team leadership", "technical mentoring", "mentoring"}:
        return any(_term_in_text(phrase, job_text) for phrase in ("mentor", "mentoring", "team leadership", "technical leadership", "lead a team"))
    if _term_in_text(term, job_text):
        return True
    displayed = _skill_display(term).lower()
    if displayed != term and _term_in_text(displayed, job_text):
        return True
    return any(_term_in_text(related, job_text) for related in RELATED_KEYWORD_SUPPORT.get(term, ()))


def _skill_supported_by_source(term, evidence_text):
    if _term_in_text(term, evidence_text):
        return True
    displayed = _skill_display(term).lower()
    if displayed != term and _term_in_text(displayed, evidence_text):
        return True
    return any(_term_in_text(related, evidence_text) for related in RELATED_KEYWORD_SUPPORT.get(term, ()))


def _expanded_job_skill_terms(job_text):
    expanded = set()
    for phrase, terms in JOB_SKILL_ALIASES.items():
        if _term_in_text(phrase, job_text):
            expanded.update(terms)
    return expanded


def _categorized_skill_lines(resume_text, job_description, custom_prompt):
    job_text = (job_description or "").lower()
    evidence_text = " ".join([resume_text or "", custom_prompt or ""]).lower()
    expanded_job_terms = _expanded_job_skill_terms(job_text)
    output = []
    seen_global = set()
    for category, terms in SKILL_CATEGORIES:
        matches = []
        for term in terms:
            is_relevant = term in expanded_job_terms or _skill_relevant_to_job(term, job_text)
            if is_relevant and _skill_supported_by_source(term, evidence_text):
                display = _skill_display(term)
                key = display.lower()
                if key == "automation" and any("automation" in item.lower() for item in matches):
                    continue
                if key not in seen_global:
                    seen_global.add(key)
                    matches.append(display)
        if matches:
            output.append(f"- {category}: {', '.join(matches[:10])}")
    return output


def _skill_line(resume_text, job_description, custom_prompt):
    categorized = _categorized_skill_lines(resume_text, job_description, custom_prompt)
    if categorized:
        return "\n".join(categorized[:9])

    keywords = _supported_target_keywords(resume_text, job_description, custom_prompt, limit=18)
    if len(keywords) < 18:
        keywords.extend(_priority_keywords(" ".join([resume_text or "", job_description or "", custom_prompt or ""]), limit=18))
    grouped = ", ".join(_keyword_display(keyword) for keyword in _dedupe_preserve_order(keywords)[:18])
    return f"- Relevant Skills: {grouped}" if grouped else ""


def _experience_bullets(resume_text, job_description):
    keywords = _priority_keywords(job_description, limit=8)
    resume_lines = [line.strip(" -•\t") for line in (resume_text or "").splitlines() if len(line.strip()) > 30]
    bullets = []
    for line in resume_lines[:6]:
        bullets.append(f"- {line}")
    if not bullets:
        bullets = [
            f"- Highlighted role responsibilities aligned with {', '.join(keywords[:3]) or 'the job requirements'}.",
            "- Emphasized delivery outcomes, collaboration, and ownership from prior work in the source resume.",
            "- Prioritized tools and technologies requested in the job description while remaining factually grounded.",
        ]
    return "\n".join(bullets)


def _keyword_display(keyword):
    special = {
        "api": "API",
        "apis": "APIs",
        "aws": "AWS",
        "gcp": "GCP",
        "ci": "CI",
        "cd": "CD",
        "sql": "SQL",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "postgresql": "PostgreSQL",
        "graphql": "GraphQL",
        "llms": "LLMs",
        "iam": "IAM",
        "pam": "PAM",
        "ai-native": "AI-native",
    }
    return special.get(keyword, keyword.title())


def _dedupe_preserve_order(values):
    result = []
    seen = set()
    for value in values:
        normalized = value.lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(value)
    return result


RELATED_KEYWORD_SUPPORT = {
    "ai-native": ("ai", "machine learning", "ml", "llm"),
    "agentic": ("ai", "automation", "workflow", "machine learning", "llm"),
    "agents": ("ai", "automation", "workflow", "machine learning", "llm"),
    "llms": ("ai", "machine learning", "openai", "language model"),
    "retrieval": ("search", "knowledge", "analytics", "data", "ai"),
    "knowledge": ("data", "analytics", "insights", "documentation"),
    "structured": ("data", "systems", "analytics", "architecture"),
    "organizational": ("workflows", "systems", "teams", "operations"),
    "internal": ("dashboard", "dashboards", "tools", "applications", "operations", "workflows"),
    "internal tools": ("dashboard", "dashboards", "tools", "applications", "operations", "workflows", "internal"),
    "design": ("designed", "architecture", "architectures", "systems", "scalable"),
    "context": ("data", "analytics", "insights", "reporting"),
    "user": ("frontend", "dashboard", "applications", "ui"),
    "insurance": ("fintech", "financial", "banking", "healthcare"),
    "prevention": ("healthcare", "health", "monitoring"),
    "iam": ("identity", "access", "security", "authentication", "authorization"),
    "pam": ("privileged", "access", "security", "identity"),
    "flask": ("python", "django", "fastapi"),
    "workflows": ("workflow", "workflows", "automation", "process"),
    "organizational": ("workflow", "workflows", "team", "teams", "operations"),
    "security": ("secure", "security", "authentication", "authorization", "access"),
}


def _keyword_supported_by_resume(keyword, resume_lower):
    if keyword in resume_lower:
        return True
    return any(signal in resume_lower for signal in RELATED_KEYWORD_SUPPORT.get(keyword, ()))


def _supported_target_keywords(resume_text, job_description, custom_prompt, limit=12):
    evidence_lower = " ".join([resume_text or "", custom_prompt or ""]).lower()
    combined_target = " ".join([job_description or "", custom_prompt or ""])
    target_keywords = _priority_keywords(combined_target, limit=40)
    supported = [keyword for keyword in target_keywords if _keyword_supported_by_resume(keyword, evidence_lower)]
    if len(supported) < limit:
        supported.extend(_priority_keywords(resume_text, limit=40))
    return _dedupe_preserve_order(supported)[:limit]


def _line_score(line, keywords):
    lower = line.lower()
    return sum(3 if keyword in lower else 0 for keyword in keywords) + min(len(line), 180) / 180


def _clean_resume_line(line):
    return re.sub(r"\s+", " ", (line or "").strip(" -â€¢\t")).strip()


def _tailor_experience_line(line, focus_terms):
    cleaned = _clean_resume_line(line)
    if not cleaned:
        return ""
    lower = cleaned.lower()
    present_terms = [term for term in focus_terms if term.lower() in lower]
    if len(present_terms) >= 2 or not focus_terms:
        return cleaned
    missing_terms = [
        term
        for term in focus_terms
        if term.lower() not in lower and _keyword_supported_by_resume(term.lower(), lower)
    ]
    if not missing_terms:
        return cleaned
    base = cleaned.rstrip(".,;")
    focus_text = " and ".join(missing_terms[:2])
    return f"{base}, supporting target-role priorities in {focus_text}."


def _is_section_heading(line, headings):
    normalized = re.sub(r"[^a-z ]+", "", (line or "").lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized in headings


def _extract_section_by_headings(text, start_headings, stop_headings):
    lines = [line.strip() for line in (text or "").splitlines()]
    collecting = False
    section_lines = []
    for line in lines:
        if not line:
            continue
        if not collecting and _is_section_heading(line, start_headings):
            collecting = True
            continue
        if collecting and _is_section_heading(line, stop_headings):
            break
        if collecting:
            section_lines.append(line)
    return "\n".join(section_lines).strip()


def _is_likely_experience_header(line):
    cleaned = _clean_resume_line(line)
    if not cleaned:
        return False
    if _looks_like_experience_header(cleaned):
        return True
    return "|" in cleaned and len(cleaned.split()) <= 14


def _format_experience_header(line):
    cleaned = _clean_resume_line(line)
    cleaned = re.sub(r"\s*\|\s*", " | ", cleaned)
    cleaned = re.sub(
        r"([a-z)])(January|February|March|April|May|June|July|August|September|October|November|December)\b",
        r"\1 | \2",
        cleaned,
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def _experience_line_is_bullet(line):
    stripped = (line or "").strip()
    return stripped.startswith(("-", "•", "*"))


def _tailor_structured_experience(source_text, focus_terms):
    output = []
    for raw_line in source_text.splitlines():
        cleaned = _clean_resume_line(raw_line)
        if not cleaned:
            continue
        if _is_likely_experience_header(cleaned):
            output.append(_format_experience_header(cleaned))
        else:
            tailored = _tailor_experience_line(cleaned, focus_terms)
            output.append(f"- {tailored}")
    return "\n".join(output)


def _fallback_ranked_experience(resume_text, keywords, focus_terms):
    resume_lines = [
        _clean_resume_line(line)
        for line in (resume_text or "").splitlines()
        if len(_clean_resume_line(line)) > 30 and not _looks_like_experience_header(line)
    ]
    ranked_lines = sorted(resume_lines, key=lambda line: _line_score(line, keywords), reverse=True)
    bullets = []
    for line in _dedupe_preserve_order(ranked_lines)[:8]:
        tailored = _tailor_experience_line(line, focus_terms)
        if tailored:
            bullets.append(f"- {tailored}")
    if not bullets:
        bullets = [
            f"- Highlighted role responsibilities aligned with {', '.join(focus_terms[:3]) or 'the job requirements'}.",
            "- Emphasized delivery outcomes, collaboration, and ownership from prior work in the source resume.",
            "- Prioritized tools and technologies requested in the job description while remaining factually grounded.",
        ]
    return "\n".join(bullets)


def _experience_start_headings():
    return {
        "professional experience",
        "work experience",
        "experience",
        "employment history",
        "work history",
        "career history",
    }


def _experience_stop_headings():
    return {
        "projects",
        "project experience",
        "key projects",
        "education",
        "academic background",
        "certifications",
        "certification",
        "licenses",
        "awards",
        "achievements",
        "credentials",
    }


def _experience_source_text(resume_text):
    section = _extract_section_by_headings(resume_text, _experience_start_headings(), _experience_stop_headings())
    if section:
        return section
    for heading in ("professional experience", "work experience", "experience", "employment history", "work history"):
        section = _find_section(resume_text, heading)
        if section:
            return section
    return ""


def _source_experience_headers(resume_text):
    source_text = _experience_source_text(resume_text)
    headers = []
    for line in source_text.splitlines():
        cleaned = _clean_resume_line(line)
        if _is_likely_experience_header(cleaned):
            headers.append(_format_experience_header(cleaned))
    return headers


def _company_token(header):
    company = (header or "").split("|", 1)[0]
    return re.sub(r"[^a-z0-9]+", " ", company.lower()).strip()


def _missing_source_experience_headers(generated_experience, resume_text):
    generated_lower = (generated_experience or "").lower()
    missing = []
    for header in _source_experience_headers(resume_text):
        company = _company_token(header)
        if company and company not in generated_lower:
            missing.append(header)
    return missing


def _experience_bullets(resume_text, job_description, custom_prompt=""):
    keywords = _supported_target_keywords(resume_text, job_description, custom_prompt, limit=12)
    focus_terms = [_keyword_display(keyword) for keyword in keywords[:6]]
    source_text = _experience_source_text(resume_text)
    if source_text:
        return _tailor_structured_experience(source_text, focus_terms)
    return _fallback_ranked_experience(resume_text, keywords, focus_terms)


def _legacy_unused_experience_bullets(resume_text, job_description):
    keywords = _priority_keywords(job_description, limit=8)
    resume_lines = [line.strip(" -â€¢\t") for line in (resume_text or "").splitlines() if len(line.strip()) > 30]
    bullets = []
    for line in resume_lines[:6]:
        bullets.append(f"- {line}")
    if not bullets:
        bullets = [
            f"- Highlighted role responsibilities aligned with {', '.join(keywords[:3]) or 'the job requirements'}.",
            "- Emphasized delivery outcomes, collaboration, and ownership from prior work in the source resume.",
            "- Prioritized tools and technologies requested in the job description while remaining factually grounded.",
        ]
    return "\n".join(bullets)


def _old_tailor_experience_line(line, focus_terms):
    cleaned = _clean_resume_line(line)
    if not cleaned:
        return ""
    return cleaned


def _projects_section(resume_text, job_description):
    existing = _find_section(resume_text, "project")
    if existing:
        return existing
    keywords = _priority_keywords(job_description, limit=6)
    focus = ", ".join(keywords[:2]) or "backend engineering and API delivery"
    return "\n".join(
        [
            f"- Selected project highlights tailored to the role with focus on {focus}.",
            "- Described architecture decisions, implementation approach, and measurable impact from real work.",
        ]
    )


def _summary_text(original_resume, job_description):
    keywords = _priority_keywords(job_description, limit=10)
    top_skills = ", ".join(keywords[:5]) or "backend development, API design, and cloud systems"
    candidate = _extract_name(original_resume)
    return (
        f"Results-focused software professional with experience presented in the source resume. "
        f"Targets opportunities requiring {top_skills}. "
        "Delivers maintainable systems with strong collaboration, quality, and ownership practices. "
        "This version is tailored for ATS readability and relevance while keeping claims grounded in provided information."
    ).replace(candidate, "Candidate")


def local_generate_resume(original_resume, job_description, custom_prompt):
    skills = _skill_line(original_resume, job_description, custom_prompt)
    education_text = _find_section(original_resume, "education")
    certifications_text = _find_section(original_resume, "certification")
    return {
        "full_name": _extract_name(original_resume),
        "contact_info": _extract_contact(original_resume),
        "professional_summary": _summary_text(original_resume, job_description),
        "technical_skills": skills or "Relevant skills from original resume and job description",
        "professional_experience": _experience_bullets(original_resume, job_description, custom_prompt),
        "projects": _projects_section(original_resume, job_description),
        "education": education_text or "Education details are included from the source resume.",
        "certifications": certifications_text or "Certifications available upon request or from source resume.",
    }


def _find_section(text, heading):
    pattern = re.compile(rf"{heading}s?\s*[:\n](.*?)(?:\n[A-Z][A-Za-z ]{{2,}}:|\Z)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text or "")
    return match.group(1).strip() if match else ""


def _openai_refinement_min_score():
    try:
        return int(os.getenv("OPENAI_REFINEMENT_MIN_SCORE", str(DEFAULT_OPENAI_REFINEMENT_MIN_SCORE)))
    except ValueError:
        return DEFAULT_OPENAI_REFINEMENT_MIN_SCORE


def _openai_chat_sections(client, messages, temperature=0.3):
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": RESUME_RESPONSE_SCHEMA,
        },
        temperature=temperature,
    )
    data = json.loads(response.choices[0].message.content)
    return {key: _normalize_whitespace(str(data.get(key, ""))) for key in SECTION_KEYS}


def _build_refinement_prompt(draft_sections, original_resume, job_description, custom_prompt, score_data):
    source_headers = _source_experience_headers(original_resume)
    missing_keywords = score_data.get("missing_keywords", [])
    return f"""Improve this generated resume draft for ATS matching and resume quality.

Current ATS score: {score_data.get("score", 0)}
Missing ATS keywords to consider, only when truthful and supported: {", ".join(missing_keywords) or "None"}

Source Work Experience headers that must all remain in professional_experience, in this order:
{chr(10).join(source_headers) or "No explicit work experience headers detected."}

Original Resume:
{original_resume}

Job Description:
{job_description}

User Instructions:
{custom_prompt or "No extra instructions."}

Current Draft JSON:
{json.dumps(draft_sections, ensure_ascii=False, indent=2)}

Revision rules:
- Return a complete JSON object with all required resume section keys.
- Preserve every source company, role title, and employment date in professional_experience.
- Keep company/role/date headers as plain lines without "- ".
- Improve bullets under each preserved role to naturally include supported missing keywords.
- Do not add fake employers, dates, titles, degrees, certifications, metrics, or tools.
- Keep the result polished and realistic for a real resume.
"""


def _score_sections(job_description, sections):
    return score_resume(job_description, render_resume_text(sections))


def _choose_better_openai_sections(draft_sections, refined_sections, original_resume, job_description, custom_prompt):
    normalized_draft = _normalize_sections(draft_sections, original_resume, job_description, custom_prompt)
    if not refined_sections:
        return normalized_draft

    normalized_refined = _normalize_sections(refined_sections, original_resume, job_description, custom_prompt)
    if _missing_source_experience_headers(normalized_refined["professional_experience"], original_resume):
        return normalized_draft

    draft_score = _score_sections(job_description, normalized_draft)["score"]
    refined_score = _score_sections(job_description, normalized_refined)["score"]
    return normalized_refined if refined_score >= draft_score else normalized_draft


def _try_openai_generate(original_resume, job_description, custom_prompt):
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI

        client = OpenAI()
        messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(original_resume, job_description, custom_prompt)},
        ]
        draft_sections = _openai_chat_sections(client, messages, temperature=0.3)
        normalized_draft = _normalize_sections(draft_sections, original_resume, job_description, custom_prompt)
        score_data = _score_sections(job_description, normalized_draft)

        if score_data["score"] >= _openai_refinement_min_score() or not score_data.get("missing_keywords"):
            return normalized_draft

        refinement_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_refinement_prompt(
                    normalized_draft,
                    original_resume,
                    job_description,
                    custom_prompt,
                    score_data,
                ),
            },
        ]
        refined_sections = _openai_chat_sections(client, refinement_messages, temperature=0.2)
        chosen_sections = _choose_better_openai_sections(
            normalized_draft,
            refined_sections,
            original_resume,
            job_description,
            custom_prompt,
        )
        refined_score = _score_sections(job_description, chosen_sections)["score"]
        logger.info("OpenAI resume generation score: first=%s final=%s", score_data["score"], refined_score)
        return chosen_sections
    except Exception as exc:
        logger.warning("OpenAI resume generation failed; using local fallback. Error: %s", exc)
        return None


def _normalize_sections(sections, original_resume, job_description, custom_prompt):
    fallback = local_generate_resume(original_resume, job_description, custom_prompt)
    normalized = {}
    for key in SECTION_KEYS:
        value = _normalize_whitespace((sections or {}).get(key, ""))
        normalized[key] = value or fallback.get(key, "")

    normalized["technical_skills"] = _skill_line(original_resume, job_description, custom_prompt)

    normalized["professional_experience"] = _normalize_experience_lines(normalized.get("professional_experience", ""))
    normalized["projects"] = _normalize_bullet_lines(normalized.get("projects", ""))

    missing_experience_headers = _missing_source_experience_headers(normalized["professional_experience"], original_resume)
    if missing_experience_headers:
        logger.info(
            "Generated resume omitted source experience headers; rebuilding experience locally. Missing: %s",
            ", ".join(missing_experience_headers),
        )
        normalized["professional_experience"] = fallback.get("professional_experience", "")

    if len([line for line in normalized["professional_experience"].splitlines() if line.strip()]) < 2:
        normalized["professional_experience"] = _experience_bullets(original_resume, job_description, custom_prompt)

    if len([line for line in normalized["projects"].splitlines() if line.strip()]) < 2:
        normalized["projects"] = _projects_section(original_resume, job_description)

    return normalized


def generate_resume_sections(original_resume, job_description, custom_prompt):
    ai_result = _try_openai_generate(original_resume, job_description, custom_prompt)
    if ai_result:
        return _normalize_sections(ai_result, original_resume, job_description, custom_prompt)
    return _normalize_sections(local_generate_resume(original_resume, job_description, custom_prompt), original_resume, job_description, custom_prompt)


def render_resume_text(sections):
    labels = {
        "full_name": "Full Name",
        "contact_info": "Contact",
        "professional_summary": "Professional Summary",
        "technical_skills": "Technical Skills",
        "professional_experience": "Professional Experience",
        "projects": "Projects",
        "education": "Education",
        "certifications": "Certifications",
    }
    parts = []
    for key in SECTION_KEYS:
        value = (sections.get(key) or "").strip()
        if value:
            parts.append(f"{labels[key]}\n{value}")
    return "\n\n".join(parts)
