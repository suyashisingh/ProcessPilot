"""Grounded retrieval with optional Watson Discovery integration."""
from dataclasses import dataclass

import httpx

from app.config import Settings


@dataclass
class Article:
    title: str
    body: str
    keywords: tuple[str, ...]


LOCAL_ARTICLES = (
    Article("Software access policy", "Managers approve access requests before IT provisions role-based access. Include the application name and business justification.", ("access", "permission", "salesforce", "application")),
    Article("Password reset guide", "Use the self-service password portal first. If locked out after identity verification, IT can reset the account.", ("password", "reset", "locked", "login")),
    Article("Leave request policy", "Submit leave dates and leave type for manager approval. Requests should normally be submitted five business days in advance.", ("leave", "vacation", "pto", "absence")),
    Article("Onboarding checklist", "HR validates the start date and manager, then IT provisions standard accounts and hardware after approval.", ("onboard", "new hire", "laptop", "employee")),
)


class KnowledgeRetriever:
    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, query: str) -> list[dict]:
        """Use configured Watson Discovery, otherwise use an intentionally small approved KB."""
        if self.settings.watson_discovery_url and self.settings.watson_discovery_apikey and self.settings.watson_discovery_project_id:
            return self._watson_search(query)
        tokens = set(query.lower().split())
        results = []
        for article in LOCAL_ARTICLES:
            matches = tokens.intersection(article.keywords)
            if matches:
                results.append({"title": article.title, "excerpt": article.body, "confidence": round(len(matches) / len(article.keywords), 2)})
        return sorted(results, key=lambda item: item["confidence"], reverse=True)[:3]

    def _watson_search(self, query: str) -> list[dict]:
        url = f"{self.settings.watson_discovery_url.rstrip('/')}/v2/projects/{self.settings.watson_discovery_project_id}/query"
        headers = {"Authorization": f"Bearer {self.settings.watson_discovery_apikey}"}
        try:
            response = httpx.post(url, headers=headers, json={"natural_language_query": query, "count": 3}, timeout=8)
            response.raise_for_status()
            return [{"title": item.get("document_title", "Watson knowledge article"), "excerpt": item.get("text", "")[:500], "confidence": item.get("result_metadata", {}).get("confidence", 0.5)} for item in response.json().get("results", [])]
        except httpx.HTTPError:
            return []
