from export_to_mremoteng import parse_devices, is_stacked_device, get_stacked_base_name

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
    assert by_name["SW-CampusA-Core"]["mfgr"] == ""
    assert by_name["SW-CampusA-Core"]["model"] == "3810M"
    assert by_name["SW-CampusA-Core"]["serial_number"] == "SG12345678"
    assert by_name["AP-Bldg1-01"]["mfgr"] == "Aruba"
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

def test_get_stacked_base_name_and_is_stacked_device():
    assert get_stacked_base_name("SW-Stack-2") == "SW-Stack"
    assert get_stacked_base_name("SW-Stack-3") == "SW-Stack"
    assert get_stacked_base_name("SW-Stack-10") == "SW-Stack"
    assert get_stacked_base_name("SW-Stack-1") is None
    assert get_stacked_base_name("SW-Stack") is None
    assert get_stacked_base_name("AP-Bldg1-02") is None
    assert get_stacked_base_name("SW-CampusB-01") is None
    assert get_stacked_base_name("") is None
    assert get_stacked_base_name(None) is None

    # is_stacked_device with commander present
    assert is_stacked_device("SW-Stack-2", {"SW-Stack", "SW-Stack-2"}) is True
    assert is_stacked_device("SW-Stack-3", {"SW-Stack", "SW-Stack-3"}) is True
    # is_stacked_device without commander present
    assert is_stacked_device("SW-Stack-2", {"OTHER", "SW-Stack-2"}) is False
    assert is_stacked_device("IDF-2", {"IDF-2"}) is False
    # is_stacked_device with all_device_names=None
    assert is_stacked_device("SW-Stack-2") is True
    assert is_stacked_device("SW-Stack") is False

def test_parse_devices_stacked_members_no_ip_excluded_by_default():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <amp:amp_ap_list xmlns:amp="http://www.airwave.com">
      <ap id="1">
        <name>SW-Stack</name>
        <lan_ip>10.10.1.1</lan_ip>
        <folder id="10"/>
        <device_category>Switch</device_category>
        <model>2930F</model>
      </ap>
      <ap id="2">
        <name>SW-Stack-2</name>
        <folder id="10"/>
        <device_category>Switch</device_category>
        <model>2930F</model>
      </ap>
      <ap id="3">
        <name>SW-Stack-3</name>
        <device_category>Switch</device_category>
        <model>2930F</model>
      </ap>
    </amp:amp_ap_list>
    """
    devices, total = parse_devices(xml, include_stacked=False)
    assert total == 3
    assert len(devices) == 1
    assert devices[0]["name"] == "SW-Stack"
    assert devices[0]["ip"] == "10.10.1.1"

def test_parse_devices_stacked_members_no_ip_included_when_flag_enabled():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <amp:amp_ap_list xmlns:amp="http://www.airwave.com">
      <ap id="1">
        <name>SW-Stack</name>
        <lan_ip>10.10.1.1</lan_ip>
        <folder id="10"/>
        <device_category>Switch</device_category>
        <model>2930F</model>
      </ap>
      <ap id="2">
        <name>SW-Stack-2</name>
        <folder id="10"/>
        <device_category>Switch</device_category>
        <model>2930F</model>
      </ap>
      <ap id="3">
        <name>SW-Stack-3</name>
        <device_category>Switch</device_category>
        <model>2930F</model>
      </ap>
    </amp:amp_ap_list>
    """
    devices, total = parse_devices(xml, include_stacked=True)
    assert total == 3
    assert len(devices) == 3
    by_name = {d["name"]: d for d in devices}

    assert "SW-Stack" in by_name
    assert "SW-Stack-2" in by_name
    assert "SW-Stack-3" in by_name

    # Check IP inheritance
    assert by_name["SW-Stack"]["ip"] == "10.10.1.1"
    assert by_name["SW-Stack-2"]["ip"] == "10.10.1.1"
    assert by_name["SW-Stack-3"]["ip"] == "10.10.1.1"

    # Check folder inheritance for SW-Stack-3 (which had no folder)
    assert by_name["SW-Stack"]["folder_id"] == "10"
    assert by_name["SW-Stack-2"]["folder_id"] == "10"
    assert by_name["SW-Stack-3"]["folder_id"] == "10"

def test_parse_devices_standalone_no_ip_still_excluded():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <amp:amp_ap_list xmlns:amp="http://www.airwave.com">
      <ap id="1">
        <name>Standalone-No-IP</name>
        <folder id="10"/>
        <model>2930F</model>
      </ap>
    </amp:amp_ap_list>
    """
    devices, total = parse_devices(xml, include_stacked=True)
    assert total == 1
    assert len(devices) == 0

def test_parse_devices_standalone_switch_with_dash_number_kept():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <amp:amp_ap_list xmlns:amp="http://www.airwave.com">
      <ap id="1">
        <name>IDF-2</name>
        <lan_ip>10.20.1.2</lan_ip>
        <folder id="10"/>
        <model>2930F</model>
      </ap>
    </amp:amp_ap_list>
    """
    devices, total = parse_devices(xml, include_stacked=False)
    assert total == 1
    assert len(devices) == 1
    assert devices[0]["name"] == "IDF-2"
    assert devices[0]["ip"] == "10.20.1.2"
