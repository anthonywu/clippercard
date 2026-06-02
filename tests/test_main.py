import json
import sys
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import clippercard.main as main
import clippercard.test_cli as test_cli


def test_cookie_jar_path_for_default_account_keeps_legacy_filename(tmp_path):
    base_path = tmp_path / "auth.cookies"

    assert main._cookie_jar_path_for_account("default", cookie_jar_path=base_path) == base_path


def test_cookie_jar_path_for_named_account_uses_section_specific_filename(tmp_path):
    base_path = tmp_path / "auth.cookies"

    assert main._cookie_jar_path_for_account("other", cookie_jar_path=base_path) == tmp_path / "auth.other.cookies"


def test_cookie_jar_path_for_named_account_sanitizes_section_name(tmp_path):
    base_path = tmp_path / "auth.cookies"

    assert (
        main._cookie_jar_path_for_account("work profile/1", cookie_jar_path=base_path)
        == tmp_path / "auth.work_profile_1.cookies"
    )


def test_get_client_auth_loads_credentials_from_keychain():
    args = SimpleNamespace(
        account="default",
        config="/does/not/exist",
        credential_store="keychain",
        username=None,
        password=None,
    )

    def fake_run(command, check=False, capture_output=False, text=False):
        assert command == [
            "security",
            "find-generic-password",
            "-s",
            main._CREDENTIAL_STORE_SERVICE,
            "-a",
            "default",
            "-w",
        ]
        assert check is False
        assert capture_output is True
        assert text is True
        return CompletedProcess(
            command,
            0,
            json.dumps({"username": "person@example.com", "password": "supersecret"}),
            "",
        )

    with (
        patch("clippercard.main.sys.platform", "darwin"),
        patch("clippercard.main.subprocess.run", new=fake_run),
    ):
        assert main._get_client_auth(args) == ("person@example.com", "supersecret")


def test_get_client_auth_migrates_config_credentials_to_keychain(tmp_path):
    config_path = tmp_path / "credentials.ini"
    config_path.write_text(
        """\
[other]
username = person@example.com
password = supersecret
"""
    )
    args = SimpleNamespace(
        account="other",
        config=str(config_path),
        credential_store="keychain",
        username=None,
        password=None,
    )
    saved = {}

    def fake_run(command, check=False, capture_output=False, text=False):
        assert check is False
        assert capture_output is True
        assert text is True
        if command[1] == "find-generic-password":
            return CompletedProcess(command, 44, "", "The specified item could not be found.")
        if command[1] == "add-generic-password":
            saved["command"] = command
            saved["payload"] = command[-1]
            return CompletedProcess(command, 0, "", "")
        raise AssertionError(f"Unexpected security command: {command}")

    with (
        patch("clippercard.main.sys.platform", "darwin"),
        patch("clippercard.main.subprocess.run", new=fake_run),
    ):
        assert main._get_client_auth(args) == ("person@example.com", "supersecret")

    assert saved["command"][:8] == [
        "security",
        "add-generic-password",
        "-U",
        "-s",
        main._CREDENTIAL_STORE_SERVICE,
        "-a",
        "other",
        "-w",
    ]
    assert json.loads(saved["payload"]) == {"username": "person@example.com", "password": "supersecret"}


def test_get_client_auth_keychain_requires_macos():
    args = SimpleNamespace(
        account="default",
        config="/does/not/exist",
        credential_store="keychain",
        username=None,
        password=None,
    )

    with (
        patch("clippercard.main.sys.platform", "linux"),
        pytest.raises(main.ClipperCardCommandError) as exc,
    ):
        main._get_client_auth(args)

    assert str(exc.value) == "macOS Keychain credential storage is only supported on macOS"


def test_get_client_auth_uses_keychain_when_config_auth_is_missing():
    args = SimpleNamespace(
        account="default",
        config="/does/not/exist",
        credential_store=None,
        username=None,
        password=None,
    )

    with (
        patch("clippercard.main._config_auth_available", return_value=False),
        patch("clippercard.main._load_keychain_auth", return_value=("person@example.com", "supersecret")),
    ):
        assert main._get_client_auth(args) == ("person@example.com", "supersecret")


def test_resolve_credential_store_falls_back_to_keychain_when_config_auth_is_missing():
    args = SimpleNamespace(
        account="default",
        config="/does/not/exist",
        credential_store=None,
        username=None,
        password=None,
    )

    with (
        patch("clippercard.main._config_auth_available", return_value=False),
        patch("clippercard.main._keychain_item_exists", return_value=True),
    ):
        assert main._resolve_credential_store(args) == "keychain"


def test_resolve_cookie_store_falls_back_to_keychain_when_cookie_file_is_missing(tmp_path):
    args = SimpleNamespace(account="other", cookie_store=None)
    expected_cookie_path = tmp_path / "auth.other.cookies"

    with (
        patch("clippercard.main._cookie_jar_path_for_account", return_value=expected_cookie_path),
        patch("clippercard.main._keychain_item_exists", return_value=True),
    ):
        assert main._resolve_cookie_store(args) == "keychain"


def test_summary_uses_account_specific_cookie_jar_path():
    expected_cookie_path = Path("/tmp/auth.other.cookies")

    class DummySession:
        reused_cookies = False
        cookie_jar_path = expected_cookie_path
        profile_info = None
        cards = []

    with (
        patch.object(sys, "argv", ["clippercard", "summary", "--account", "other"]),
        patch("clippercard.main._get_client_auth", return_value=("person@example.com", "supersecret")),
        patch("clippercard.main._cookie_jar_path_for_account", return_value=expected_cookie_path) as cookie_path_mock,
        patch("clippercard.main.clippercard.Session", return_value=DummySession()) as session_mock,
        patch("clippercard.main.clippercard.porcelain.tabular_output", return_value="summary output"),
        patch("clippercard.main.sys.stdout.isatty", return_value=True),
        patch("clippercard.main.print") as print_mock,
    ):
        main.main()

    cookie_path_mock.assert_called_once_with("other")
    session_mock.assert_called_once_with(
        "person@example.com",
        "supersecret",
        cookie_jar_path=expected_cookie_path,
        cookie_store="file",
        keychain_account="other",
    )
    print_mock.assert_called_once_with("summary output")


def test_summary_can_use_keychain_cookie_store():
    expected_cookie_path = Path("/tmp/auth.other.cookies")

    class DummySession:
        reused_cookies = False
        cookie_jar_path = expected_cookie_path
        profile_info = None
        cards = []

    with (
        patch.object(sys, "argv", ["clippercard", "summary", "--account", "other", "--cookie-store", "keychain"]),
        patch("clippercard.main._get_client_auth", return_value=("person@example.com", "supersecret")),
        patch("clippercard.main._cookie_jar_path_for_account", return_value=expected_cookie_path),
        patch("clippercard.main.clippercard.Session", return_value=DummySession()) as session_mock,
        patch("clippercard.main.clippercard.porcelain.tabular_output", return_value="summary output"),
        patch("clippercard.main.sys.stdout.isatty", return_value=True),
        patch("clippercard.main.print"),
    ):
        main.main()

    session_mock.assert_called_once_with(
        "person@example.com",
        "supersecret",
        cookie_jar_path=expected_cookie_path,
        cookie_store="keychain",
        keychain_account="other",
    )


def test_summary_can_output_json_without_cookie_message_on_stdout(capsys):
    expected_cookie_path = Path("/tmp/auth.cookies")

    class DummySession:
        reused_cookies = True
        cookie_jar_path = expected_cookie_path
        profile_info = None
        cards = []

    with (
        patch.object(sys, "argv", ["clippercard", "summary", "--output", "json"]),
        patch("clippercard.main._get_client_auth", return_value=("person@example.com", "supersecret")),
        patch("clippercard.main._cookie_jar_path_for_account", return_value=expected_cookie_path),
        patch("clippercard.main.clippercard.Session", return_value=DummySession()),
        patch("clippercard.main.clippercard.porcelain.summary_json_output", return_value='{"cards": []}'),
    ):
        main.main()

    output = capsys.readouterr()
    assert output.out == '{"cards": []}\n'
    assert output.err == f"Reusing saved cookies from {expected_cookie_path}\n"


def test_summary_defaults_to_json_when_stdout_is_piped(capsys):
    expected_cookie_path = Path("/tmp/auth.cookies")

    class DummySession:
        reused_cookies = True
        cookie_jar_path = expected_cookie_path
        profile_info = None
        cards = []

    with (
        patch.object(sys, "argv", ["clippercard", "summary"]),
        patch("clippercard.main._get_client_auth", return_value=("person@example.com", "supersecret")),
        patch("clippercard.main._cookie_jar_path_for_account", return_value=expected_cookie_path),
        patch("clippercard.main.clippercard.Session", return_value=DummySession()),
        patch("clippercard.main.clippercard.porcelain.summary_json_output", return_value='{"cards": []}'),
        patch("clippercard.main.sys.stdout.isatty", return_value=False),
    ):
        main.main()

    output = capsys.readouterr()
    assert output.out == '{"cards": []}\n'
    assert output.err == f"Reusing saved cookies from {expected_cookie_path}\n"


def test_summary_output_table_overrides_pipe_detection(capsys):
    expected_cookie_path = Path("/tmp/auth.cookies")

    class DummySession:
        reused_cookies = True
        cookie_jar_path = expected_cookie_path
        profile_info = None
        cards = []

    with (
        patch.object(sys, "argv", ["clippercard", "summary", "--output", "table"]),
        patch("clippercard.main._get_client_auth", return_value=("person@example.com", "supersecret")),
        patch("clippercard.main._cookie_jar_path_for_account", return_value=expected_cookie_path),
        patch("clippercard.main.clippercard.Session", return_value=DummySession()),
        patch("clippercard.main.clippercard.porcelain.tabular_output", return_value="summary output"),
        patch("clippercard.main.sys.stdout.isatty", return_value=False),
    ):
        main.main()

    output = capsys.readouterr()
    assert output.out == f"Reusing saved cookies from {expected_cookie_path}\nsummary output\n"
    assert output.err == ""


def test_main_cli_only_exposes_summary_subcommand():
    parser = main._build_parser()
    subcommands = parser._subparsers._group_actions[0].choices

    assert set(subcommands) == {"summary"}


def test_main_cli_rejects_fixture_subcommands():
    with (
        patch.object(sys, "argv", ["clippercard", "parse-dashboard", "dashboard.html"]),
        pytest.raises(SystemExit) as exc,
    ):
        main.main()

    assert exc.value.code == 2


def test_test_cli_exposes_fixture_subcommands():
    parser = test_cli._build_parser()
    subcommands = parser._subparsers._group_actions[0].choices

    assert set(subcommands) == {"parse-dashboard", "parse-profile"}


def test_test_cli_parse_dashboard_uses_dashboard_parser():
    with (
        patch.object(sys, "argv", ["clippercard-test", "parse-dashboard", "dashboard.html"]),
        patch("clippercard.test_cli.open", create=True) as open_mock,
        patch(
            "clippercard.test_cli.clippercard.parser.parse_dashboard_cards",
            return_value=["card"],
        ) as parse_mock,
        patch(
            "clippercard.test_cli.clippercard.porcelain.tabular_output",
            return_value="dashboard output",
        ) as output_mock,
        patch("clippercard.test_cli.print") as print_mock,
    ):
        open_mock.return_value.__enter__.return_value.read.return_value = "<html></html>"
        test_cli.main()

    parse_mock.assert_called_once_with("<html></html>")
    output_mock.assert_called_once_with(None, ["card"])
    print_mock.assert_called_once_with("dashboard output")


def test_test_cli_parse_profile_uses_profile_parser():
    with (
        patch.object(sys, "argv", ["clippercard-test", "parse-profile", "profile.html"]),
        patch("clippercard.test_cli.open", create=True) as open_mock,
        patch(
            "clippercard.test_cli.clippercard.parser.parse_profile_page",
            return_value={"name": "Profile"},
        ) as parse_mock,
        patch(
            "clippercard.test_cli.clippercard.porcelain.tabular_output",
            return_value="profile output",
        ) as output_mock,
        patch("clippercard.test_cli.print") as print_mock,
    ):
        open_mock.return_value.__enter__.return_value.read.return_value = "<html></html>"
        test_cli.main()

    parse_mock.assert_called_once_with("<html></html>")
    output_mock.assert_called_once_with({"name": "Profile"}, None)
    print_mock.assert_called_once_with("profile output")
