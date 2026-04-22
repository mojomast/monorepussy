"""External integrations and third-party APIs."""

import os
from typing import Dict, Optional


class GitHubClient:
    """GitHub API client."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")

    def get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def get_repo(self, owner: str, repo: str) -> Dict:
        """Get repository information."""
        import requests

        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.get_headers())
        return response.json()

    def get_issues(self, owner: str, repo: str, state: str = "open") -> list:
        """Get repository issues."""
        import requests

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        response = requests.get(
            url, headers=self.get_headers(), params={"state": state}
        )
        return response.json()


class StripeClient:
    """Stripe API client for payments."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STRIPE_API_KEY")

    def create_customer(self, email: str, name: str) -> Dict:
        """Create a Stripe customer."""
        import stripe

        stripe.api_key = self.api_key
        return stripe.Customer.create(email=email, name=name)

    def create_subscription(self, customer_id: str, price_id: str) -> Dict:
        """Create a subscription."""
        import stripe

        stripe.api_key = self.api_key
        return stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
        )
