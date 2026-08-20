import nox

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]


def _uv_sync(session: nox.Session) -> None:
    """Install into the nox session venv, not the project .venv."""
    session.run("uv", "sync", "--group", "dev", "--locked", external=True)


@nox.session(python="3.14")
def test(session: nox.Session) -> None:
    """Run tests with pytest (current version only)."""
    _uv_sync(session)
    session.run("pytest")


@nox.session(python=PYTHON_VERSIONS)
def test_all(session: nox.Session) -> None:
    """Run tests across all Python versions."""
    _uv_sync(session)
    session.run("pytest")


@nox.session(python="3.14")
def lint(session: nox.Session) -> None:
    """Run linting with ruff."""
    _uv_sync(session)
    session.run("ruff", "check", ".")


@nox.session(python="3.14")
def format(session: nox.Session) -> None:
    """Format code with ruff."""
    _uv_sync(session)
    session.run("ruff", "format", ".")
