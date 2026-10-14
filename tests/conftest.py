import os
import sys

# Ensure repository root is on sys.path so modules like export_to_mremoteng can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

@pytest.fixture
def sample_folder_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<amp:amp_folder_list xmlns:amp="http://www.airwave.com">
  <folder id="1">
    <name>Top</name>
    <parent_id>0</parent_id>
  </folder>
  <folder id="10">
    <name>Campus A</name>
    <parent_id>1</parent_id>
  </folder>
  <folder id="20">
    <name>Campus B</name>
    <parent_id>1</parent_id>
  </folder>
  <folder id="101">
    <name>Building 1</name>
    <parent_id>10</parent_id>
  </folder>
  <folder id="102">
    <name>Building 2</name>
    <parent_id>10</parent_id>
  </folder>
  <folder id="1011">
    <name>Floor 1</name>
    <parent_id>101</parent_id>
  </folder>
  <folder id="201">
    <name>Building 1</name>
    <parent_id>20</parent_id>
  </folder>
</amp:amp_folder_list>
"""

@pytest.fixture
def sample_ap_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<amp:amp_ap_list xmlns:amp="http://www.airwave.com">
  <ap id="1001">
    <name>SW-CampusA-Core</name>
    <lan_ip>10.10.1.1</lan_ip>
    <folder id="10"/>
    <device_category>Switch</device_category>
    <model>Aruba 3810M</model>
    <serial_number>SG12345678</serial_number>
  </ap>
  <ap id="1002">
    <name>AP-Bldg1-01</name>
    <ip>10.10.2.1</ip>
    <folder id="101"/>
    <device_category>thin_ap</device_category>
    <model>AP 535</model>
    <serial_number>CN87654321</serial_number>
  </ap>
  <ap id="1003">
    <name>AP-Bldg1-02</name>
    <remote_lan_ip>10.10.2.2</remote_lan_ip>
    <folder id="1011"/>
    <device_category>thin_ap</device_category>
    <model>AP 515</model>
    <serial_number></serial_number>
  </ap>
  <ap id="1004">
    <name>SW-CampusB-01</name>
    <lan_ip>10.20.1.1</lan_ip>
    <folder id="201"/>
    <device_category>Switch</device_category>
    <model>Aruba 2930F</model>
    <serial_number>SG99999999</serial_number>
  </ap>
  <ap id="1005">
    <name>(id:1005) Ignored AP</name>
    <lan_ip>10.10.99.1</lan_ip>
    <folder id="10"/>
    <device_category>thin_ap</device_category>
    <model>AP 305</model>
  </ap>
  <ap id="1006">
    <name>AP-No-IP</name>
    <folder id="10"/>
    <device_category>thin_ap</device_category>
    <model>AP 305</model>
  </ap>
  <ap id="1007">
    <name>AP-Unassigned</name>
    <lan_ip>10.99.99.99</lan_ip>
    <folder id="999"/>
    <device_category>Access Point</device_category>
    <model>AP 505</model>
    <serial_number>SN00000001</serial_number>
  </ap>
</amp:amp_ap_list>
"""
