import re

# this will be used to remove the filler words from the query, e.g., "um", "uh", "like", "you know", "i mean", "so", "well"
# it can strengthen the query and make it more concise, which can help the retrieval and reranking stages to find more relevant chunks

FILLER_WORDS = [
    "um", "uh", "like", "you know", "i mean", "so", "well",
    "actually", "basically", "literally", "right", "okay",
]

ABBREVIATIONS = {
    "sso": "single sign-on",
    "vpn": "virtual private network",
    "mfa": "multi-factor authentication",
    "mtu": "maximum transmission unit",
    "hr": "human resources",
    "po": "purchase order",
    "coa": "certificate of analysis",
    "pqi": "procurement quality index",
    "dpo": "data protection officer",
    "dlp": "data leak prevention",
    "rag": "retrieval augmented generation",
    "llm": "large language model",
    "drm": "disaster recovery",
    "rto": "recovery time objective",
    "rpo": "recovery point objective",
    "hvac": "heating ventilation air conditioning",
    "crac": "computer room air conditioning",
    "rfid": "radio frequency identification",
    "rbac": "role based access control",
    "ap": "access point",
    "nic": "network interface card",
    "isp": "internet service provider",
    "csirt": "cyber security incident response team",
    "soc": "security operations center",
    "erp": "enterprise resource planning",
    "lms": "learning management system",
    "ssr": "server side rendering",
    "ci": "continuous integration",
    "cd": "continuous deployment",
    "cicd": "continuous integration continuous deployment",
    "gdpr": "general data protection regulation",
    "ccpa": "california consumer privacy act",
    "pii": "personally identifiable information",
    "ai": "artificial intelligence",
}

ERROR_CODE_PATTERN = re.compile(r'(ERR|SOP|VPN|SEC|CODE|FORM|FLAG)[\-_]?[A-Z0-9\-_]+', re.IGNORECASE)

FORM_CODE_PATTERN = re.compile(r'Form\s+([A-Z]+-[A-Z]+-\d+)', re.IGNORECASE)

URL_PATTERN = re.compile(r'https?://[^\s]+')

FILLER_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(f) for f in FILLER_WORDS) + r')\b',
    re.IGNORECASE
)


def normalize_query(query: str) -> str:
    original = query

    query = FILLER_PATTERN.sub('', query)

    query = URL_PATTERN.sub(lambda m: f"[URL]", query)

    def expand_abbrev(match):
        word = match.group(0)
        lower = word.lower()
        if lower in ABBREVIATIONS:
            return f"{word} ({ABBREVIATIONS[lower]})"
        return word

    query = re.sub(r'\b[A-Z]{2,}\b', expand_abbrev, query)

    query = re.sub(r'\s+', ' ', query).strip()

    return query


def extract_metadata_hints(query: str) -> dict:
    hints = {}

    query_lower = query.lower()

    error_codes = ERROR_CODE_PATTERN.findall(query)
    if error_codes:
        hints["error_codes"] = [code.upper() for code in error_codes]

    form_codes = FORM_CODE_PATTERN.findall(query)
    if form_codes:
        hints["form_codes"] = [code.upper() for code in form_codes]

    chapter = detect_chapter(query_lower)
    if chapter:
        hints["chapter"] = chapter

    return hints


def detect_chapter(query_lower: str) -> str | None:
    chapter_keywords = {
        "Chapter 1": [
            "sso", "authentication", "lockout", "network", "packet loss",
            "nic", "driver", "802.1x", "port security", "access point",
            "rogue ap", "channel", "wifi", "wireless", "err-ssop",
            "err-radius", "sop-net", "infrastructure", "identity",
        ],
        "Chapter 2": [
            "vpn", "remote work", "cyber", "phishing", "tunnel",
            "ipsec", "ssl", "tls", "mtu", "isp", "timeout",
            "suspicious email", "credential", "csirt",
        ],
        "Chapter 3": [
            "payroll", "salary", "hr", "benefits", "grievance",
            "compensation", "leave", "onboarding", "insurance",
            "ombudsman", "anti-retaliation", "hr-pay", "hr-med",
        ],
        "Chapter 4": [
            "cleanroom", "rfid", "server room", "temperature",
            "hvac", "crac", "access denied", "badge", "airlock",
            "facility", "alarm-temp", "cooling", "thermal",
        ],
        "Chapter 5": [
            "vendor", "procurement", "purchase order", "po",
            "shipment", "coa", "certificate of analysis", "bid",
            "contract", "tender", "pqi", "proc-rej", "proc-eth",
        ],
        "Chapter 6": [
            "laravel", "react", "cicd", "ci/cd", "migration",
            "code", "deployment", "pipeline", "hydration",
            "phpunit", "jest", "testing", "coverage", "rollback",
        ],
        "Chapter 7": [
            "privacy", "gdpr", "ccpa", "data breach", "erasure",
            "right to be forgotten", "cross-border", "dpo",
            "cloud-isolate", "pii", "compliance", "priv-req",
        ],
        "Chapter 8": [
            "expense", "receipt", "audit", "fraud", "reimbursement",
            "corporate card", "travel", "missing receipt", "affidavit",
            "fin-exp", "fin-audit", "disbursement", "vp approval",
        ],
        "Chapter 9": [
            "evacuation", "fire", "disaster", "dr failover",
            "power outage", "blackout", "ups", "dns", "bgp",
            "rto", "rpo", "dr-failover", "assembly area", "warden",
        ],
        "Chapter 10": [
            "ai", "dlp", "rag", "prompt", "governance",
            "clipboard", "data leak", "bias", "audit",
            "sec-dlp", "ai-gov", "grounding", "hallucination",
        ],
    }

    scores = {}
    for chapter, keywords in chapter_keywords.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scores[chapter] = score

    if scores:
        return max(scores, key=scores.get)
    return None
