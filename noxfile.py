import nox

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14", "3.15"]


@nox.session(python="3.14")
def test(session: nox.Session) -> None:
    """Run tests with pytest (current version only)."""
    session.run("uv", "sync", "--group", "dev", external=True)
    session.run("uv", "run", "pytest", external=True)


@nox.session(python=PYTHON_VERSIONS)
def test_all(session: nox.Session) -> None:
    """Run tests across all Python versions."""
    session.run("uv", "sync", "--group", "dev", external=True)
    session.run("uv", "run", "pytest", external=True)


@nox.session(python="3.14")
def lint(session: nox.Session) -> None:
    """Run linting with ruff."""
    session.run("uv", "sync", "--group", "dev", external=True)
    session.run("uv", "run", "ruff", "check", ".", external=True)


@nox.session(python="3.14")
def format(session: nox.Session) -> None:
    """Format code with ruff."""
    session.run("uv", "sync", "--group", "dev", external=True)
    session.run("uv", "run", "ruff", "format", ".", external=True)


@nox.session(python="3.14")
def build(session: nox.Session) -> None:
    """Build distributions."""
    session.run("uv", "sync", "--group", "dev", external=True)
    session.run("uv", "run", "python", "-m", "build", external=True)
