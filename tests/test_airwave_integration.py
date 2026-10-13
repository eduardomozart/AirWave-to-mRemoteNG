import sys
import os
from unittest.mock import MagicMock, patch
import pytest
from export_to_mremoteng import main

class MockResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

def test_main_url_normalization_and_e2e(sample_folder_xml, sample_ap_xml, tmp_path, monkeypatch, capsys):
    out_file = str(tmp_path / "output.xml")
    test_args = [
        "export_to_mremoteng.py",
        "-i", "10.0.0.5",
        "-u", "admin",
        "-p", "secret",
        "-o", out_file
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    mock_client = MagicMock()
    mock_client.login.return_value = MockResponse(status_code=200)
    mock_client.folder_list.return_value = MockResponse(status_code=200, text=sample_folder_xml)
    mock_client.ap_list.return_value = MockResponse(status_code=200, text=sample_ap_xml)

    with patch("export_to_mremoteng.AirWaveAPIClient", return_value=mock_client) as mock_client_cls:
        main()

        # Check URL was normalized to https://10.0.0.5
        mock_client_cls.assert_called_once_with(username="admin", password="secret", url="https://10.0.0.5")
        mock_client.login.assert_called_once()
        mock_client.folder_list.assert_called_once()
        mock_client.ap_list.assert_called_once()
        mock_client.logout.assert_called_once()

    assert os.path.exists(out_file)
    captured = capsys.readouterr()
    assert "File successfully created" in captured.out
    assert "Parsed 6 folders." in captured.out
    assert "Parsed 5 devices" in captured.out

def test_main_url_preserves_protocol(sample_folder_xml, sample_ap_xml, tmp_path, monkeypatch):
    out_file = str(tmp_path / "output.xml")
    test_args = [
        "export_to_mremoteng.py",
        "-i", "https://airwave.local:8443",
        "-u", "admin",
        "-p", "secret",
        "-o", out_file
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    mock_client = MagicMock()
    mock_client.login.return_value = MockResponse(status_code=200)
    mock_client.folder_list.return_value = MockResponse(status_code=200, text=sample_folder_xml)
    mock_client.ap_list.return_value = MockResponse(status_code=200, text=sample_ap_xml)

    with patch("export_to_mremoteng.AirWaveAPIClient", return_value=mock_client) as mock_client_cls:
        main()
        mock_client_cls.assert_called_once_with(username="admin", password="secret", url="https://airwave.local:8443")

def test_main_login_failure(monkeypatch, capsys):
    test_args = ["export_to_mremoteng.py", "-i", "10.0.0.5", "-u", "admin", "-p", "wrong"]
    monkeypatch.setattr(sys, "argv", test_args)

    mock_client = MagicMock()
    mock_client.login.return_value = MockResponse(status_code=401)

    with patch("export_to_mremoteng.AirWaveAPIClient", return_value=mock_client):
        main()

    captured = capsys.readouterr()
    assert "AirWave login failed with status code 401" in captured.out
    mock_client.folder_list.assert_not_called()

def test_main_connect_exception(monkeypatch, capsys):
    test_args = ["export_to_mremoteng.py", "-i", "10.0.0.5", "-u", "admin", "-p", "secret"]
    monkeypatch.setattr(sys, "argv", test_args)

    mock_client = MagicMock()
    mock_client.login.side_effect = ConnectionError("Connection refused")

    with patch("export_to_mremoteng.AirWaveAPIClient", return_value=mock_client):
        main()

    captured = capsys.readouterr()
    assert "Error connecting to AirWave: Connection refused" in captured.out
    mock_client.folder_list.assert_not_called()

def test_main_folder_filter_by_path(sample_folder_xml, sample_ap_xml, tmp_path, monkeypatch, capsys):
    out_file = str(tmp_path / "output_filtered.xml")
    test_args = [
        "export_to_mremoteng.py",
        "-i", "10.0.0.5",
        "-u", "admin",
        "-p", "secret",
        "-o", out_file,
        "-f", "Campus B > Building 1"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    mock_client = MagicMock()
    mock_client.login.return_value = MockResponse(status_code=200)
    mock_client.folder_list.return_value = MockResponse(status_code=200, text=sample_folder_xml)
    mock_client.ap_list.return_value = MockResponse(status_code=200, text=sample_ap_xml)

    with patch("export_to_mremoteng.AirWaveAPIClient", return_value=mock_client):
        main()

    assert os.path.exists(out_file)
    with open(out_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Campus B > Building 1 has device SW-CampusB-01
    assert "SW-CampusB-01" in xml_content
    # Devices from Campus A should not be included
    assert "SW-CampusA-Core" not in xml_content

def test_main_nonexistent_folder_warning(sample_folder_xml, sample_ap_xml, tmp_path, monkeypatch, capsys):
    out_file = str(tmp_path / "output_nonexistent.xml")
    test_args = [
        "export_to_mremoteng.py",
        "-i", "10.0.0.5",
        "-u", "admin",
        "-p", "secret",
        "-o", out_file,
        "-f", "NonExistentFolder"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    mock_client = MagicMock()
    mock_client.login.return_value = MockResponse(status_code=200)
    mock_client.folder_list.return_value = MockResponse(status_code=200, text=sample_folder_xml)
    mock_client.ap_list.return_value = MockResponse(status_code=200, text=sample_ap_xml)

    with patch("export_to_mremoteng.AirWaveAPIClient", return_value=mock_client):
        main()

    captured = capsys.readouterr()
    assert "Warning: None of the specified AirWave folders were found." in captured.out
    assert not os.path.exists(out_file)
