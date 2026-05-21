import os


def absolute_url(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path

    if path.startswith("/uploads"):
        public_base_url = os.getenv("PUBLIC_BACKEND_URL", "").strip()
        if public_base_url:
            return f"{public_base_url.rstrip('/')}{path}"

    return path
