import requests
from time import sleep
from typing import Optional, Dict, Any


class NewsAPIClient():
    def __init__(self, api_key: str, base_url: str, endpoints: Dict[str, str], retries: int, timeout: int, logger):
        self.api_key = api_key
        self.base_url = base_url
        self.endpoints = endpoints
        self.retries = retries
        self.timeout = timeout
        self.logger = logger
        
    def _make_request(self, endpoint: str, method: str = 'GET', params: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        for attempt in range(self.retries):
            try:
                response = requests.request(method, url, params=params, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url} with error: {e}")
                if attempt < self.retries - 1:
                    sleep(2)
                else:
                    self.logger.error(f"API request failed for {url} after {self.retries} attempts")
                    raise

    def fetch_news(self, platform) -> Dict[str, Any]:
        endpoint = self.endpoints[platform]
        headers = {
            "x-rapidapi-key": self.api_key
        }
        return self._make_request(endpoint, method='GET', headers=headers)

    def fetch_and_prepare_news(self, platform):
        data = self.fetch_news(platform)
        if data and isinstance(data, dict):
            data = data["results"]

        prepared_data = []
        for item in data:
            try:
                prepared_data.append({
                    "title": item["title"] if "title" in item else item["headline"],
                    "date": item["date"] if "date" in item else item["pubDate"] if "pubDate" in item else "",
                    "image": item["image"] if "image" in item else item["imageUrl"] if "imageUrl" in item else "",
                    "content": item["content"] if "content" in item else "",
                    "url": item["url"] if "url" in item else "",
                    "source": platform
                })
            except:
                self.logger.error(f"Missing key during preparation")
                raise

        return prepared_data
