"""
Firecrawl-backed website ingestion for company strategy simulations.
"""

import hashlib
import ipaddress
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from urllib import error, parse, request

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.firecrawl')


class FirecrawlIngestionError(RuntimeError):
    """Raised when website ingestion cannot produce usable content."""


@dataclass
class FirecrawlPage:
    """Normalized representation of a crawled website page."""
    url: str
    title: str
    markdown: str

    def to_document_text(self) -> str:
        return (
            "=== Website Page ===\n"
            "Source Type: Website\n"
            f"Source URL: {self.url}\n"
            f"Page Title: {self.title}\n\n"
            f"{self.markdown}"
        ).strip()


@dataclass
class FirecrawlIngestionResult:
    """Final normalized crawl output used by ontology generation."""
    normalized_url: str
    crawl_status: str
    page_count: int
    page_urls: List[str]
    document_texts: List[str]
    combined_text: str
    warnings: List[str] = field(default_factory=list)


class FirecrawlIngestionService:
    """Server-side Firecrawl integration for website ingestion."""

    _LOW_VALUE_PATH_KEYWORDS = (
        '/login', '/signin', '/sign-in', '/signup', '/sign-up',
        '/account', '/cart', '/checkout', '/privacy', '/terms',
        '/cookie', '/cookies', '/legal', '/gdpr'
    )

    _LOW_VALUE_TITLE_KEYWORDS = (
        'login', 'sign in', 'sign up', 'account', 'cart', 'checkout',
        'privacy', 'terms', 'cookie', 'legal'
    )

    def __init__(self):
        self.api_key = Config.FIRECRAWL_API_KEY
        self.base_url = Config.FIRECRAWL_BASE_URL.rstrip('/')

    def ensure_configured(self) -> None:
        if not self.api_key:
            raise FirecrawlIngestionError(
                "Website ingestion requires FIRECRAWL_API_KEY on the backend."
            )

    def validate_company_url(self, raw_url: str) -> str:
        """Validate and normalize a public company root URL."""
        candidate = (raw_url or '').strip()
        if not candidate:
            raise FirecrawlIngestionError("Please provide a company website URL.")

        parsed = parse.urlsplit(candidate)
        if parsed.scheme not in {'http', 'https'}:
            raise FirecrawlIngestionError("The company website URL must use http or https.")
        if not parsed.hostname:
            raise FirecrawlIngestionError("The company website URL must include a valid hostname.")
        if parsed.username or parsed.password:
            raise FirecrawlIngestionError("The company website URL cannot include embedded credentials.")
        if parsed.query or parsed.fragment:
            raise FirecrawlIngestionError("Use a clean root website URL without query strings or fragments.")
        if parsed.path not in {'', '/'}:
            raise FirecrawlIngestionError("Provide the company root website URL, not a specific subpage.")

        hostname = parsed.hostname.lower()
        if hostname in {'localhost'} or hostname.endswith('.local'):
            raise FirecrawlIngestionError("The company website URL must be publicly reachable.")

        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            ip = None

        if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast):
            raise FirecrawlIngestionError("The company website URL must not point to a private or local network.")

        port = f":{parsed.port}" if parsed.port else ''
        return f"{parsed.scheme}://{hostname}{port}/"

    def crawl(self, raw_url: str) -> FirecrawlIngestionResult:
        """Run Firecrawl crawl and convert the result into ontology-ready text blocks."""
        self.ensure_configured()
        normalized_url = self.validate_company_url(raw_url)
        logger.info("Starting Firecrawl crawl for %s", normalized_url)

        crawl_id = self._start_crawl(normalized_url)
        final_payload = self._poll_crawl(crawl_id)
        raw_pages = self._collect_pages(crawl_id, final_payload)
        normalized_pages, warnings = self._normalize_pages(normalized_url, raw_pages)

        if not normalized_pages:
            raise FirecrawlIngestionError(
                "Firecrawl completed but did not return enough usable website content. "
                "Try a cleaner company homepage or add uploaded documents."
            )

        crawl_status = final_payload.get('status') or 'completed'
        if warnings or crawl_status not in {'completed'}:
            crawl_status = 'partial'

        document_texts = [page.to_document_text() for page in normalized_pages]
        combined_text = "\n\n".join(document_texts)

        logger.info(
            "Firecrawl crawl finished for %s with %s usable pages (%s)",
            normalized_url,
            len(normalized_pages),
            crawl_status,
        )

        return FirecrawlIngestionResult(
            normalized_url=normalized_url,
            crawl_status=crawl_status,
            page_count=len(normalized_pages),
            page_urls=[page.url for page in normalized_pages],
            document_texts=document_texts,
            combined_text=combined_text,
            warnings=warnings,
        )

    def _start_crawl(self, normalized_url: str) -> str:
        payload = {
            "url": normalized_url,
            "limit": Config.FIRECRAWL_CRAWL_LIMIT,
            "maxDiscoveryDepth": Config.FIRECRAWL_MAX_DISCOVERY_DEPTH,
            "allowExternalLinks": False,
            "allowSubdomains": False,
            "scrapeOptions": {
                "formats": ["markdown"],
                "onlyMainContent": True,
            },
        }
        response = self._request_json('POST', '/v2/crawl', payload)
        crawl_id = response.get('id')
        if not crawl_id:
            raise FirecrawlIngestionError("Firecrawl did not return a crawl job id.")
        return crawl_id

    def _poll_crawl(self, crawl_id: str) -> Dict[str, Any]:
        deadline = time.monotonic() + Config.FIRECRAWL_TIMEOUT_SECONDS
        last_payload: Dict[str, Any] = {}

        while time.monotonic() < deadline:
            payload = self._request_json('GET', f'/v2/crawl/{crawl_id}')
            last_payload = payload
            status = (payload.get('status') or '').lower()

            if status in {'completed', 'partial'}:
                return payload
            if status in {'failed', 'cancelled', 'error'}:
                raise FirecrawlIngestionError(
                    payload.get('error') or f"Firecrawl crawl failed with status: {status}"
                )

            time.sleep(Config.FIRECRAWL_POLL_INTERVAL_SECONDS)

        raise FirecrawlIngestionError(
            f"Firecrawl crawl timed out after {Config.FIRECRAWL_TIMEOUT_SECONDS} seconds."
        )

    def _collect_pages(self, crawl_id: str, first_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        pages: List[Dict[str, Any]] = []
        payload = first_payload
        seen_cursors = set()

        while True:
            payload_pages = payload.get('data') or []
            if isinstance(payload_pages, list):
                pages.extend(payload_pages)

            next_cursor = payload.get('next')
            if not next_cursor or next_cursor in seen_cursors:
                break

            seen_cursors.add(next_cursor)
            encoded_cursor = parse.quote(str(next_cursor), safe='')
            payload = self._request_json('GET', f'/v2/crawl/{crawl_id}?next={encoded_cursor}')

        return pages

    def _normalize_pages(
        self,
        normalized_url: str,
        raw_pages: List[Dict[str, Any]],
    ) -> tuple[List[FirecrawlPage], List[str]]:
        parsed_root = parse.urlsplit(normalized_url)
        root_host = self._normalize_host(parsed_root.hostname or '')
        seen_hashes = set()
        normalized_pages: List[FirecrawlPage] = []
        warnings: List[str] = []

        for raw_page in raw_pages:
            page_url = (raw_page.get('url') or '').strip()
            markdown = (raw_page.get('markdown') or '').strip()
            title = (raw_page.get('title') or '').strip()

            if not page_url or not markdown:
                continue

            parsed_page = parse.urlsplit(page_url)
            page_host = self._normalize_host(parsed_page.hostname or '')
            if not page_host or page_host != root_host:
                continue
            if self._is_low_value_path(parsed_page.path):
                continue

            normalized_markdown = self._normalize_markdown(markdown)
            word_count = len(normalized_markdown.split())
            if word_count < Config.FIRECRAWL_MIN_PAGE_WORDS:
                warnings.append(f"Skipped low-signal page: {page_url}")
                continue

            title_text = title or self._title_from_url(page_url)
            if self._is_low_value_title(title_text):
                continue

            page_hash = hashlib.sha256(normalized_markdown.encode('utf-8')).hexdigest()
            if page_hash in seen_hashes:
                continue

            seen_hashes.add(page_hash)
            normalized_pages.append(
                FirecrawlPage(
                    url=page_url,
                    title=title_text,
                    markdown=normalized_markdown[:Config.FIRECRAWL_MAX_PAGE_CHARACTERS],
                )
            )

        return normalized_pages, warnings

    def _request_json(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        body = None
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
        }

        if payload is not None:
            body = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(req, timeout=Config.FIRECRAWL_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode('utf-8'))
        except error.HTTPError as exc:
            details = exc.read().decode('utf-8', errors='ignore')
            raise FirecrawlIngestionError(
                f"Firecrawl request failed ({exc.code}): {details or exc.reason}"
            ) from exc
        except error.URLError as exc:
            raise FirecrawlIngestionError(f"Unable to reach Firecrawl: {exc.reason}") from exc

    def _normalize_markdown(self, markdown: str) -> str:
        lines = []
        previous_blank = False
        for line in markdown.splitlines():
            stripped = line.strip()
            if not stripped:
                if previous_blank:
                    continue
                previous_blank = True
                lines.append("")
                continue

            previous_blank = False
            lines.append(stripped)

        return "\n".join(lines).strip()

    def _title_from_url(self, page_url: str) -> str:
        parsed = parse.urlsplit(page_url)
        path = parsed.path.strip('/') or parsed.netloc
        last_segment = path.split('/')[-1]
        title = last_segment.replace('-', ' ').replace('_', ' ').strip()
        return title.title() or parsed.netloc

    def _is_low_value_path(self, path: str) -> bool:
        lowered = (path or '').lower()
        return any(keyword in lowered for keyword in self._LOW_VALUE_PATH_KEYWORDS)

    def _is_low_value_title(self, title: str) -> bool:
        lowered = (title or '').lower()
        return any(keyword in lowered for keyword in self._LOW_VALUE_TITLE_KEYWORDS)

    def _normalize_host(self, hostname: str) -> str:
        return hostname.lower().rstrip('.')
