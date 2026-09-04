"""Version stamping, which the container build relies on.

The images no longer ship .git or a git binary, so generate() has to fall back
to SUNSYNK_API_CLIENT_VERSION instead of raising.
"""
import subprocess

import pytest

from sunsynk.version_info import Version


@pytest.fixture(autouse=True)
def version_file(tmp_path, monkeypatch):
    """Never let a test overwrite the real sunsynk/version.py."""
    path = tmp_path / "version.py"
    monkeypatch.setattr("sunsynk.version_info.VERSION_FILENAME", str(path))
    return path


def fake_git(monkeypatch, *, stdout=b"", returncode=0, error=None):
    class FakeProcess:
        returncode = None

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def communicate(self):
            return stdout, b""

    def popen(*_args, **_kwargs):
        if error is not None:
            raise error
        process = FakeProcess()
        process.returncode = returncode
        return process

    monkeypatch.setattr(subprocess, "Popen", popen)


def test_a_tag_becomes_the_version(monkeypatch, version_file):
    fake_git(monkeypatch, stdout=b"v1.2.3\n")
    assert Version.generate() == "1.2.3"
    assert 'SUNSYNK_API_CLIENT_VERSION = "1.2.3"' in version_file.read_text(encoding="utf-8")


def test_commits_since_the_tag_are_folded_into_the_version(monkeypatch):
    fake_git(monkeypatch, stdout=b"v1.2.3-4-gdeadbee\n")
    assert Version.generate() == "1.2.3.4"


def test_a_missing_git_binary_falls_back_to_the_env_var(monkeypatch):
    # This is the container build: no .git, no git executable.
    fake_git(monkeypatch, error=FileNotFoundError("git"))
    monkeypatch.setenv("SUNSYNK_API_CLIENT_VERSION", "v2.5.0")
    assert Version.generate() == "2.5.0"


def test_a_failed_git_describe_falls_back_to_the_env_var(monkeypatch):
    fake_git(monkeypatch, stdout=b"", returncode=128)
    monkeypatch.setenv("SUNSYNK_API_CLIENT_VERSION", "abc1234")
    # Anything that is not a dotted number becomes a local version segment.
    assert Version.generate() == "0.0.0+abc1234"


def test_without_git_or_an_env_var_the_version_is_zero(monkeypatch):
    fake_git(monkeypatch, error=OSError("no exec"))
    monkeypatch.delenv("SUNSYNK_API_CLIENT_VERSION", raising=False)
    assert Version.generate() == "0.0.0"


def test_an_existing_version_file_beats_the_env_var(monkeypatch, version_file):
    version_file.write_text('SUNSYNK_API_CLIENT_VERSION = "3.1.4"\n', encoding="utf-8")
    fake_git(monkeypatch, error=FileNotFoundError("git"))
    monkeypatch.setenv("SUNSYNK_API_CLIENT_VERSION", "9.9.9")
    assert Version.generate() == "3.1.4"
