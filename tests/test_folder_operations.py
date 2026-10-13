from export_to_mremoteng import flatten_folders_by_name, build_tree

def test_flatten_folders_single_candidate():
    folders = {
        "10": {"name": "Campus A", "parent_id": "1", "subfolders": [], "devices": []},
        "101": {"name": "Switch", "parent_id": "10", "subfolders": [], "devices": []},
    }
    devices = [
        {"name": "SW-01", "ip": "10.10.1.1", "folder_id": "101", "model": "2930F", "serial_number": ""}
    ]

    flatten_folders_by_name(folders, devices, ["Switch"])

    # Folder 101 should be removed
    assert "101" not in folders
    # Device should be reassigned to parent "10"
    assert devices[0]["folder_id"] == "10"

def test_flatten_folders_preserves_multiple_candidates():
    # If a parent contains both 'Switch' and 'Access Point', neither should be flattened
    folders = {
        "10": {"name": "Campus A", "parent_id": "1", "subfolders": [], "devices": []},
        "101": {"name": "Switch", "parent_id": "10", "subfolders": [], "devices": []},
        "102": {"name": "Access Point", "parent_id": "10", "subfolders": [], "devices": []},
    }
    devices = [
        {"name": "SW-01", "ip": "10.10.1.1", "folder_id": "101", "model": "2930F", "serial_number": ""},
        {"name": "AP-01", "ip": "10.10.1.2", "folder_id": "102", "model": "AP 535", "serial_number": ""}
    ]

    flatten_folders_by_name(folders, devices, ["Switch", "Access Point"])

    # Both folders should be kept
    assert "101" in folders
    assert "102" in folders
    assert devices[0]["folder_id"] == "101"
    assert devices[1]["folder_id"] == "102"

def test_flatten_folders_deep_hierarchy():
    # Grandparent -> Parent (Switch) -> Child (Floor 1)
    folders = {
        "10": {"name": "Campus A", "parent_id": None, "subfolders": [], "devices": []},
        "101": {"name": "Switch", "parent_id": "10", "subfolders": [], "devices": []},
        "1011": {"name": "Floor 1", "parent_id": "101", "subfolders": [], "devices": []},
    }
    devices = [
        {"name": "SW-01", "ip": "10.10.1.1", "folder_id": "101", "model": "2930F", "serial_number": ""}
    ]

    flatten_folders_by_name(folders, devices, ["Switch"])

    assert "101" not in folders
    assert devices[0]["folder_id"] == "10"
    # Child subfolder should be reassigned to grandparent
    assert folders["1011"]["parent_id"] == "10"

def test_build_tree_hierarchy_and_devices():
    folders = {
        "10": {"name": "Campus A", "parent_id": None, "subfolders": [], "devices": []},
        "101": {"name": "Building 1", "parent_id": "10", "subfolders": [], "devices": []},
        "20": {"name": "Campus B", "parent_id": None, "subfolders": [], "devices": []},
    }
    devices = [
        {"name": "Dev-01", "ip": "10.10.1.1", "folder_id": "101", "model": "AP 535", "serial_number": ""},
        {"name": "Dev-02", "ip": "10.20.1.1", "folder_id": "20", "model": "2930F", "serial_number": ""},
    ]

    roots = build_tree(folders, devices)

    assert set(roots) == {"10", "20"}
    assert folders["10"]["subfolders"] == ["101"]
    assert len(folders["101"]["devices"]) == 1
    assert folders["101"]["devices"][0]["name"] == "Dev-01"
    assert len(folders["20"]["devices"]) == 1
    assert folders["20"]["devices"][0]["name"] == "Dev-02"

def test_build_tree_unassigned_devices():
    folders = {
        "10": {"name": "Campus A", "parent_id": None, "subfolders": [], "devices": []},
    }
    devices = [
        {"name": "Dev-Orphan", "ip": "10.99.1.1", "folder_id": "999", "model": "AP 505", "serial_number": ""}
    ]

    roots = build_tree(folders, devices)

    assert "default" in roots
    assert "default" in folders
    assert folders["default"]["name"] == "Unassigned Devices"
    assert len(folders["default"]["devices"]) == 1
    assert folders["default"]["devices"][0]["name"] == "Dev-Orphan"
