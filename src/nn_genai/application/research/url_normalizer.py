from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}


def normalize_url(url: str) -> str:
    """
       Normalizers :

        Hostname casing.
        Trailing slashes.
        URL fragments.
        Tracking parameters.
        Query-parameter ordering.
        Default ports.

    """
    parsed = urlsplit(url.strip())

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()

    if scheme not in {"http", "https"} or not hostname:
        raise ValueError(f"Unsupported evidence URL: {url}")

    port = parsed.port
    if port and not (
        scheme == "http" and port == 80
        or scheme == "https" and port == 443
    ):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_parameters = [
        (key, value)
        for key, value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
        if not key.lower().startswith("utm_")
        and key.lower() not in TRACKING_PARAMETERS
    ]

    query = urlencode(sorted(query_parameters))

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            query,
            "", 
        )
    )
