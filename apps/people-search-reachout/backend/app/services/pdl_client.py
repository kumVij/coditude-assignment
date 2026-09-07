"""
People Data Labs (PDL) Person Search client.

Docs: https://docs.peopledatalabs.com/docs/person-search-api
Auth: header "X-Api-Key: <key>"
Endpoint: GET/POST https://api.peopledatalabs.com/v5/person/search
Query language: Elasticsearch query DSL against PDL's schema
  (job_title, job_company_name, location_locality, skills, etc.)

To keep this assignment runnable without a paid/live PDL subscription, the
client falls back to MOCK MODE (settings.effective_mock_mode) and returns
deterministic, realistic-looking sample people. Swapping in a different
provider (Apollo.io / Proxycurl / Coresignal) only requires implementing the
same `search_people()` signature — the rest of the app is provider-agnostic.
"""
from __future__ import annotations

import random
from typing import Any, Optional

import httpx

PDL_SEARCH_URL = "https://api.peopledatalabs.com/v5/person/search"

_MOCK_FIRST_NAMES = ["Aisha", "Rahul", "Priya", "Daniel", "Meera", "Arjun", "Sofia", "Karan", "Neha", "Wei"]
_MOCK_LAST_NAMES = ["Sharma", "Kumar", "Patel", "Chen", "Fernandes", "Iyer", "Gupta", "Nair", "Singh", "Rao"]
_MOCK_COMPANIES = ["Nimbus Labs", "Quanta Systems", "Bluepeak", "Solvix", "Northstar Tech", "Vertex Cloud"]
_MOCK_CITIES = ["Bengaluru, India", "Pune, India", "Hyderabad, India", "Mumbai, India", "Remote, India"]


class PeopleSearchError(Exception):
    pass


def _mock_search(titles: list[str], skills: list[str], location_query: str, limit: int) -> list[dict]:
    random.seed(hash((tuple(titles), tuple(skills), location_query)) % (2**32))
    results = []
    title_pool = titles or ["Software Engineer"]
    for i in range(limit):
        first, last = random.choice(_MOCK_FIRST_NAMES), random.choice(_MOCK_LAST_NAMES)
        title = random.choice(title_pool).title()
        phone_suffix = "".join(random.choice("0123456789") for _ in range(10))
        results.append(
            {
                "full_name": f"{first} {last}",
                "job_title": title,
                "job_company_name": random.choice(_MOCK_COMPANIES),
                "location_name": location_query or random.choice(_MOCK_CITIES),
                "linkedin_url": f"https://linkedin.com/in/{first.lower()}-{last.lower()}-{i}",
                "work_email": f"{first.lower()}.{last.lower()}@example.com",
                "mobile_phone": f"+91{phone_suffix}",
                "skills": skills[:5],
                "_mock": True,
            }
        )
    return results


def search_people(
    *,
    api_key: str,
    mock_mode: bool,
    titles: list[str],
    skills: list[str],
    location_query: str = "",
    limit: int = 10,
) -> list[dict]:
    if mock_mode or not api_key:
        return _mock_search(titles, skills, location_query, limit)

    # Build a PDL Elasticsearch-DSL query: match any of the parsed titles,
    # and (optionally) filter by location + boost on skills.
    should_titles = [{"match": {"job_title": t}} for t in titles] or [{"match_all": {}}]
    must: list[dict[str, Any]] = [{"bool": {"should": should_titles, "minimum_should_match": 1}}]
    if location_query:
        must.append({"match": {"location_name": location_query}})
    if skills:
        must.append({"terms": {"skills": skills}})

    query = {"query": {"bool": {"must": must}}, "size": limit}

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                PDL_SEARCH_URL,
                headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
                json=query,
            )
    except httpx.HTTPError as e:
        raise PeopleSearchError(f"Network error calling PDL: {e}") from e

    if resp.status_code >= 400:
        raise PeopleSearchError(f"PDL API error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    return data.get("data", [])


def normalize_person(raw: dict) -> dict:
    """Map a PDL (or mock) person record into our SourcedCandidate fields."""
    personal_emails = raw.get("personal_emails") or []
    email = raw.get("work_email") or (personal_emails[0] if personal_emails else "")
    phone_numbers = raw.get("phone_numbers") or []
    mobile = raw.get("mobile_phone") or (phone_numbers[0] if phone_numbers else "")

    return {
        "full_name": raw.get("full_name") or "Unknown",
        "job_title": raw.get("job_title") or "",
        "company": raw.get("job_company_name") or "",
        "location": raw.get("location_name") or "",
        "linkedin_url": raw.get("linkedin_url") or "",
        "email": email,
        "mobile_number": mobile,
        "source": "mock" if raw.get("_mock") else "pdl",
        "raw_data": raw,
    }
