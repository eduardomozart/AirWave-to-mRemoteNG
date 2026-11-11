import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from extras.airwave_ap_detail import parse_args, main


def test_parse_args_missing_ap_id(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["airwave_ap_detail.py"])
    with pytest.raises(SystemExit) as exc:
        parse_args()
    assert exc.value.code != 0


def test_parse_args_minimal(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["airwave_ap_detail.py", "123"])
    args = parse_args()
    assert args.ap_id == "123"
    assert args.url == "https://airwave"
    assert args.username is None
    assert args.password is None
    assert args.out is None


def test_parse_args_custom(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "airwave_ap_detail.py",
            "1001",
            "--url",
            "https://10.0.0.5",
            "-u",
            "admin",
            "-p",
            "secret",
            "-o",
            "test_output.xml",
        ],
    )
    args = parse_args()
    assert args.ap_id == "1001"
    assert args.url == "https://10.0.0.5"
    assert args.username == "admin"
    assert args.password == "secret"
    assert args.out == "test_output.xml"


def test_parse_args_windows_help(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["airwave_ap_detail.py", "/?"])
    with pytest.raises(SystemExit) as exc:
        parse_args()
    assert exc.value.code == 0


def test_main_success(monkeypatch, tmp_path):
    output_file = tmp_path / "custom_ap_detail.xml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "airwave_ap_detail.py",
            "42",
            "--url",
            "10.0.0.10",
            "-u",
            "testuser",
            "-p",
            "testpass",
            "-o",
            str(output_file),
        ],
    )

    mock_client = MagicMock()
    login_resp = MagicMock(status_code=200)
    mock_client.login.return_value = login_resp

    detail_resp = MagicMock(
        url="https://10.0.0.10/api/ap_detail.xml?id=42",
        status_code=200,
        text="<amp:ap_detail id='42'><name>TestAP</name></amp:ap_detail>",
    )
    mock_client.ap_detail.return_value = detail_resp

    with patch("extras.airwave_ap_detail.AirWaveAPIClient", return_value=mock_client) as mock_client_cls:
        res = main()
        assert res == 0
        mock_client_cls.assert_called_once_with(
            username="testuser",
            password="testpass",
            url="https://10.0.0.10",
            verify=False,
        )
        mock_client.login.assert_called_once()
        mock_client.ap_detail.assert_called_once_with("42")
        mock_client.logout.assert_called_once()

    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == detail_resp.text


def test_main_success_without_out(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "airwave_ap_detail.py",
            "42",
            "--url",
            "10.0.0.10",
            "-u",
            "testuser",
            "-p",
            "testpass",
        ],
    )

    mock_client = MagicMock()
    login_resp = MagicMock(status_code=200)
    mock_client.login.return_value = login_resp

    detail_resp = MagicMock(
        url="https://10.0.0.10/api/ap_detail.xml?id=42",
        status_code=200,
        text="<amp:ap_detail id='42'><name>TestAP</name></amp:ap_detail>",
    )
    mock_client.ap_detail.return_value = detail_resp

    with patch("extras.airwave_ap_detail.AirWaveAPIClient", return_value=mock_client):
        res = main()
        assert res == 0

    # Ensure no xml file was written to working directory
    assert list(tmp_path.glob("*.xml")) == []

    # Ensure raw XML was printed to stdout
    captured = capsys.readouterr()
    assert detail_resp.text in captured.out


def test_main_login_failure(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "airwave_ap_detail.py",
            "42",
            "-u",
            "testuser",
            "-p",
            "wrongpass",
        ],
    )

    mock_client = MagicMock()
    login_resp = MagicMock(status_code=401)
    mock_client.login.return_value = login_resp

    with patch("extras.airwave_ap_detail.AirWaveAPIClient", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            main()
        assert "[ERROR] Login failed (HTTP 401)" in str(exc.value)
