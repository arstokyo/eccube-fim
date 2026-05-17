from fim.template import render_email_body, render_slack_body, render_subject


def _detection(path="index.twig", full_path="/shop/index.twig", diff="+tampered line"):
    return {
        "path": path,
        "full_path": full_path,
        "root_path": "/shop",
        "git_status": " M index.twig",
        "diff": diff,
        "mtime": "2026-05-15 12:00:00 JST",
        "sha256": "abc123",
    }


def test_render_email_body_single_file_contains_path_and_diff():
    body = render_email_body("host-a", [_detection()])
    assert "/shop/index.twig" in body
    assert "+tampered line" in body


def test_render_email_body_multi_file_lists_all_paths_and_diffs():
    detections = [
        _detection(full_path="/shop/index.twig", diff="+change-one"),
        _detection(path="admin.twig", full_path="/shop/admin.twig", diff="+change-two"),
    ]
    body = render_email_body("host-a", detections)
    assert "/shop/index.twig" in body
    assert "/shop/admin.twig" in body
    assert "+change-one" in body
    assert "+change-two" in body
    assert "2 件" in body


def test_render_slack_body_contains_full_diff():
    body = render_slack_body("host-a", [_detection()])
    assert "+tampered line" in body


def test_render_slack_body_multi_file_contains_all_diffs():
    detections = [
        _detection(diff="+change-one"),
        _detection(path="admin.twig", full_path="/shop/admin.twig", diff="+change-two"),
    ]
    body = render_slack_body("host-a", detections)
    assert "+change-one" in body
    assert "+change-two" in body


def test_render_subject_contains_alert():
    assert "[ALERT]" in render_subject("host-a")
