from enum import IntEnum
from urllib.parse import urlsplit


class SourceQuality(IntEnum):
    OTHER = 0
    SECONDARY = 1
    AUTHORITATIVE = 2
    PRIMARY = 3


PRIMARY_DOMAINS = frozenset(
    {
        "nobelprize.org",
    }
)

AUTHORITATIVE_SUFFIXES = (
    ".gov",
    ".edu",
    ".ac.uk",
)

REPUTABLE_SECONDARY_DOMAINS = frozenset(
    {
        "britannica.com",
        "wikipedia.org",
    }
)


def normalize_hostname(url: str) -> str:
    hostname = urlsplit(url).hostname or ""
    return hostname.lower().removeprefix("www.")


def is_domain_or_subdomain(
    hostname: str,
    expected_domain: str,
) -> bool:
    return (
        hostname == expected_domain
        or hostname.endswith(f".{expected_domain}")
    )


def classify_source_quality(url: str) -> SourceQuality:
    hostname = normalize_hostname(url)

    if any(
        is_domain_or_subdomain(hostname, domain)
        for domain in PRIMARY_DOMAINS
    ):
        return SourceQuality.PRIMARY

    if hostname.endswith(AUTHORITATIVE_SUFFIXES):
        return SourceQuality.AUTHORITATIVE

    if any(
        is_domain_or_subdomain(hostname, domain)
        for domain in REPUTABLE_SECONDARY_DOMAINS
    ):
        return SourceQuality.SECONDARY

    return SourceQuality.OTHER
