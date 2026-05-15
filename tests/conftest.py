import subprocess
import pytest
from fim.config import Config, NotifyEmail, NotifySlack
from fim.db import Db


@pytest.fixture
def repo(tmp_path):
    """Empty git repo in a temp directory."""
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init"], cwd=r, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=r, check=True)
    return r


@pytest.fixture
def cfg(repo):
    """Minimal valid Config pointing at a temp git repo."""
    return Config(
        root_path=str(repo),
        target_files=["index.twig"],
        email=NotifyEmail(smtp_host="localhost", recipients=["a@b.com"], from_addr="fim@b.com"),
        slack=NotifySlack(),
    )


@pytest.fixture
def db(tmp_path):
    return Db(str(tmp_path / "state.db"))
