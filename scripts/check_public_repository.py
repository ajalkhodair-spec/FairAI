import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def repository_url():
    for line in Path("CITATION.cff").read_text(encoding="utf-8").splitlines():
        if line.startswith("repository-code:"):
            return line.split(":", 1)[1].strip().strip('"')
    raise RuntimeError("CITATION.cff does not define repository-code")


def main():
    url = repository_url()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "FairAI-public-access-check/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            final_url = response.geturl()
    except urllib.error.HTTPError as exc:
        status = exc.code
        final_url = exc.geturl()
    except urllib.error.URLError as exc:
        print(
            json.dumps(
                {
                    "repository_url": url,
                    "anonymously_accessible": False,
                    "error": str(exc),
                },
                indent=2,
            )
        )
        return 2
    accessible = status == 200
    print(
        json.dumps(
            {
                "repository_url": url,
                "final_url": final_url,
                "http_status": status,
                "anonymously_accessible": accessible,
                "authenticated_state_used": False,
            },
            indent=2,
        )
    )
    return 0 if accessible else 1


if __name__ == "__main__":
    sys.exit(main())
