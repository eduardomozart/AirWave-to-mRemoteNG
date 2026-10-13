import sys
import pytest
from export_to_mremoteng import parse_args, VERSION

def test_parse_args_required(monkeypatch):
    test_args = ["export_to_mremoteng.py", "-i", "10.0.0.1", "-u", "admin", "-p", "secret"]
    monkeypatch.setattr(sys, "argv", test_args)
    args = parse_args()
    assert args.ip == "10.0.0.1"
    assert args.username == "admin"
    assert args.password == "secret"
    assert args.output == "mRemoteNG_AirWave.xml"
    assert args.airwave_folder is None
    assert args.flatten_folder is None
    assert args.device_category is None
    assert args.model is None
    assert args.debug is False

def test_parse_args_missing_required(monkeypatch):
    test_args = ["export_to_mremoteng.py", "-i", "10.0.0.1", "-u", "admin"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit) as exc:
        parse_args()
    assert exc.value.code == 1

def test_parse_args_all_options(monkeypatch):
    test_args = [
        "export_to_mremoteng.py",
        "-i", "https://airwave.example.com:443",
        "-u", "api_user",
        "-p", "secure_pass",
        "-o", "custom_output.xml",
        "-f", "Campus A",
        "-f", "Top > Campus B > Building 1",
        "-l", "Switch",
        "-l", "Access Point",
        "-c", "switch",
        "-c", "controller",
        "-m", "AP 535",
        "-m", "3810M",
        "-d"
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    args = parse_args()
    assert args.ip == "https://airwave.example.com:443"
    assert args.username == "api_user"
    assert args.password == "secure_pass"
    assert args.output == "custom_output.xml"
    assert args.airwave_folder == ["Campus A", "Top > Campus B > Building 1"]
    assert args.flatten_folder == ["Switch", "Access Point"]
    assert args.device_category == ["switch", "controller"]
    assert args.model == ["AP 535", "3810M"]
    assert args.debug is True

def test_parse_args_windows_help_flag(monkeypatch):
    test_args = ["export_to_mremoteng.py", "/?"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit) as exc:
        parse_args()
    assert exc.value.code == 0
