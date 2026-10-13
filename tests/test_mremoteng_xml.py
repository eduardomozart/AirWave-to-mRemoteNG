import xml.etree.ElementTree as ET
import os
import uuid
from export_to_mremoteng import create_mremoteng_xml

def test_create_mremoteng_xml(tmp_path):
    out_file = str(tmp_path / "test_connections.xml")

    folders = {
        "10": {
            "name": "Campus A",
            "parent_id": None,
            "subfolders": ["101", "102"],
            "devices": [
                {"name": "SW-Core", "ip": "10.10.1.1", "folder_id": "10", "model": " Aruba 3810M ", "serial_number": "SG123"}
            ]
        },
        "101": {
            "name": "Building 1",
            "parent_id": "10",
            "subfolders": [],
            "devices": [
                {"name": "AP-01", "ip": "10.10.2.1", "folder_id": "101", "model": "AP 535", "serial_number": ""}
            ]
        },
        "102": {
            "name": "Empty Building",
            "parent_id": "10",
            "subfolders": [],
            "devices": []  # Empty folder should be pruned
        }
    }
    root_folders = ["10"]

    create_mremoteng_xml(folders, root_folders, out_path=out_file)

    assert os.path.exists(out_file)
    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert content.startswith('<?xml version="1.0" encoding="utf-8"?>')

    tree = ET.parse(out_file)
    root = tree.getroot()

    # Namespace check
    assert root.tag == "{http://mremoteng.org}Connections"
    assert root.get("Name") == "Connections"
    assert root.get("ConfVersion") == "2.6"
    assert root.get("EncryptionEngine") == "AES"

    # Hierarchy: Campus A container
    campus_el = root.find("Node")
    assert campus_el is not None
    assert campus_el.get("Name") == "Campus A"
    assert campus_el.get("Type") == "Container"

    # Check child nodes under Campus A
    children = list(campus_el)
    # Empty Building (102) should be removed, leaving Building 1 (101) and SW-Core
    child_names = [c.get("Name") for c in children]
    assert "Empty Building" not in child_names
    assert "Building 1" in child_names
    assert "SW-Core" in child_names

    # Check connection properties for SW-Core
    sw_node = next(c for c in children if c.get("Name") == "SW-Core")
    assert sw_node.get("Type") == "Connection"
    assert sw_node.get("Hostname") == "10.10.1.1"
    assert sw_node.get("Port") == "22"
    assert sw_node.get("Protocol") == "SSH2"
    # Leading space stripped + serial number appended
    assert sw_node.get("Descr") == "Aruba 3810M (S/N: SG123)"

    # Check required default properties on nodes to prevent mRemoteNG NullReferenceException
    required_keys = [
        "Username", "Domain", "Password", "Hostname", "Protocol", "PuttySession", "Port",
        "Colors", "Resolution", "InheritPassword", "InheritUsername", "InheritPort"
    ]
    for key in required_keys:
        assert key in sw_node.attrib
        assert key in campus_el.attrib

    # Check device under Building 1
    bldg_node = next(c for c in children if c.get("Name") == "Building 1")
    bldg_children = list(bldg_node)
    assert len(bldg_children) == 1
    ap_node = bldg_children[0]
    assert ap_node.get("Name") == "AP-01"
    assert ap_node.get("Descr") == "AP 535"
