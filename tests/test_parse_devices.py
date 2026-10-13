from export_to_mremoteng import parse_devices

def test_parse_devices_all(sample_ap_xml):
    devices, total = parse_devices(sample_ap_xml)
    # Total APs parsed in sample_ap_xml: 7
    assert total == 7
    # Out of 7, 1 is ignored ((id:1005)), 1 has no IP, so 5 devices should be kept
    assert len(devices) == 5

    device_names = [d["name"] for d in devices]
    assert "SW-CampusA-Core" in device_names
    assert "AP-Bldg1-01" in device_names
    assert "AP-Bldg1-02" in device_names
    assert "SW-CampusB-01" in device_names
    assert "AP-Unassigned" in device_names
    assert "(id:1005) Ignored AP" not in device_names
    assert "AP-No-IP" not in device_names

def test_parse_devices_ip_precedence(sample_ap_xml):
    devices, _ = parse_devices(sample_ap_xml)
    by_name = {d["name"]: d for d in devices}

    # lan_ip
    assert by_name["SW-CampusA-Core"]["ip"] == "10.10.1.1"
    # ip
    assert by_name["AP-Bldg1-01"]["ip"] == "10.10.2.1"
    # remote_lan_ip
    assert by_name["AP-Bldg1-02"]["ip"] == "10.10.2.2"

def test_parse_devices_serial_and_folder(sample_ap_xml):
    devices, _ = parse_devices(sample_ap_xml)
    by_name = {d["name"]: d for d in devices}

    assert by_name["SW-CampusA-Core"]["folder_id"] == "10"
    assert by_name["SW-CampusA-Core"]["model"] == "Aruba 3810M"
    assert by_name["SW-CampusA-Core"]["serial_number"] == "SG12345678"

    assert by_name["AP-Bldg1-02"]["serial_number"] == ""

def test_parse_devices_category_filter(sample_ap_xml):
    devices, total = parse_devices(sample_ap_xml, device_categories=["switch"])
    assert total == 7
    assert len(devices) == 2
    names = {d["name"] for d in devices}
    assert names == {"SW-CampusA-Core", "SW-CampusB-01"}

def test_parse_devices_model_filter(sample_ap_xml):
    devices, total = parse_devices(sample_ap_xml, models=["AP 535"])
    assert total == 7
    assert len(devices) == 1
    assert devices[0]["name"] == "AP-Bldg1-01"

def test_parse_devices_category_or_model_filter(sample_ap_xml):
    devices, total = parse_devices(sample_ap_xml, device_categories=["switch"], models=["AP 535"])
    assert total == 7
    # 2 switches + 1 AP 535
    assert len(devices) == 3
    names = {d["name"] for d in devices}
    assert names == {"SW-CampusA-Core", "SW-CampusB-01", "AP-Bldg1-01"}

def test_parse_devices_malformed_xml():
    devices, total = parse_devices("<invalid><xml")
    assert devices == []
    assert total == 0

def test_parse_devices_with_aplist_instance(sample_ap_xml):
    from airwaveapiclient import APList
    ap_list = APList(sample_ap_xml)
    devices, total = parse_devices(ap_list)
    assert total == 7
    assert len(devices) == 5

def test_parse_devices_dict_model():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <amp:amp_ap_list xmlns:amp="http://www.airwave.com">
      <ap id="1">
        <name>AP-With-Dict-Model</name>
        <lan_ip>10.0.0.1</lan_ip>
        <model id="296">AP 105</model>
        <folder id="10"/>
      </ap>
    </amp:amp_ap_list>
    """
    devices, total = parse_devices(xml)
    assert total == 1
    assert len(devices) == 1
    assert devices[0]["model"] == "AP 105"
    assert devices[0]["folder_id"] == "10"
