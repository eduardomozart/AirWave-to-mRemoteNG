import xml.etree.ElementTree as ET
from pyairwave.awapi import ArubaAirwave
import urllib3
import os
import argparse
import sys

urllib3.disable_warnings()

def parse_args():
    """
    Auxiliary function to handle command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Export AirWave switches to mRemoteNG XML format.")
    parser.add_argument('-i', '--ip', required=True, help="AirWave Server IP or Hostname")
    parser.add_argument('-u', '--username', required=True, help="AirWave API Username")
    parser.add_argument('-p', '--password', required=True, help="AirWave API Password")
    parser.add_argument('-o', '--output', default="mRemoteNG_AirWave.xml", help="Output XML file name (default: mRemoteNG_AirWave.xml)")
    parser.add_argument('-m', '--master-folder', help="Wrap all exported nodes in a master folder with this name (e.g., 'AirWave Sync')")
    parser.add_argument('-d', '--dry-run', action='store_true', help="Only test the AirWave connection and print raw XML fields (does not create an XML file)")
    
    try:
        args = parser.parse_args()
    except SystemExit:
        print("\nWarning: Missing required arguments. Please provide --ip, --username, and --password.")
        sys.exit(1)
        
    return args

def parse_folders(xml_data):
    """
    Parses folder_list.xml to extract folders and build a hierarchy.
    Returns a dict: {folder_id: {'name': folder_name, 'parent_id': parent_id, 'subfolders': [], 'devices': []}}
    """
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"Error parsing folder list XML: {e}")
        return {}

    folders = {}
    for folder_el in root.iter('folder'):
        fid = folder_el.get('id')
        name = folder_el.findtext('name')
        parent_id = folder_el.findtext('parent_id')
        if fid:
            folders[fid] = {
                'name': name or "Unknown Folder", 
                'parent_id': parent_id, 
                'subfolders': [], 
                'devices': []
            }
    return folders

def parse_devices(xml_data):
    """
    Parses ap_detail.xml to extract devices (APs).
    Returns a list of dicts: [{'name': ..., 'ip': ..., 'folder_id': ...}, ...]
    """
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"Error parsing AP detail XML: {e}")
        return []

    devices = []
    for ap_el in root.iter('ap'):
        name = ap_el.findtext('name')
        
        # IP could be in <lan_ip>, <ip>, or <remote_lan_ip>
        ip = ap_el.findtext('lan_ip') or ap_el.findtext('ip') or ap_el.findtext('remote_lan_ip') or ""
        
        # folder ID is typically an attribute in <folder id="...">
        folder_id = None
        folder_el = ap_el.find('folder')
        if folder_el is not None:
            folder_id = folder_el.get('id')
                
        # We need to filter for switches. We will check the XML tags to ensure we only grab switches.
        # This tag might be <device_category>, <type>, or <model>. We'll finalize this once we test.
        device_category = ap_el.findtext('device_category')
        model = ap_el.findtext('model')
        
        # Placeholder condition: checking if "switch" is in device_category or model
        # We will adjust this exact condition based on your test output.
        is_switch = False
        if device_category and 'switch' in device_category.lower():
            is_switch = True
        if model and 'switch' in model.lower():
            is_switch = True
            
        if not is_switch:
            continue
            
        devices.append({'name': name, 'ip': ip, 'folder_id': folder_id})
    return devices

def build_tree(folders, devices):
    """
    Links subfolders to their parents and assigns devices to folders.
    Returns a list of root folder IDs.
    """
    root_folders = []
    
    # Link subfolders
    for fid, fdata in folders.items():
        pid = fdata['parent_id']
        # If parent exists and is not the current folder itself
        if pid and pid in folders and pid != fid:
            folders[pid]['subfolders'].append(fid)
        else:
            root_folders.append(fid)
            
    # Assign devices
    for dev in devices:
        fid = dev['folder_id']
        if fid in folders:
            folders[fid]['devices'].append(dev)
        else:
            # If a device has no valid folder, create a "Default Folder" or add it to root
            if "default" not in folders:
                folders["default"] = {
                    'name': 'Unassigned Devices', 
                    'parent_id': None, 
                    'subfolders': [], 
                    'devices': []
                }
                root_folders.append("default")
            folders["default"]['devices'].append(dev)
            
    return root_folders

def create_mremoteng_xml(folders, root_folders, out_path="mRemoteNG_AirWave.xml", master_folder_name=None):
    """
    Generates mRemoteNG compatible XML file.
    """
    root = ET.Element("Connections", Name="Connections", Export="False", ConfVersion="2.6")
    
    # If a master folder name is provided, wrap everything inside it. Otherwise, attach directly to root.
    target_parent = root
    if master_folder_name:
        target_parent = ET.SubElement(root, "Node", 
                                      Name=master_folder_name, 
                                      Type="Container", 
                                      Expanded="True")
    
    def add_node(parent_el, folder_id):
        fdata = folders[folder_id]
        container = ET.SubElement(parent_el, "Node", 
                                  Name=fdata['name'], 
                                  Type="Container", 
                                  Expanded="True")
        
        # Add subfolders recursively
        for sub_id in fdata['subfolders']:
            add_node(container, sub_id)
            
        # Add devices
        for dev in fdata['devices']:
            dev_name = dev['name'] or dev['ip'] or "Unknown Device"
            # Some essential properties to prevent mRemoteNG from complaining
            ET.SubElement(container, "Node", 
                          Name=dev_name, 
                          Type="Connection", 
                          Hostname=dev['ip'] or "", 
                          Protocol="SSH2", 
                          Port="22",
                          PuttySession="Default Settings",
                          Username="",
                          Domain="",
                          Password="",
                          MacAddress="",
                          UserField="")

    for rf in root_folders:
        add_node(target_parent, rf)
        
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ", level=0)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"File successfully created: {os.path.abspath(out_path)}")

def main():
    args = parse_args()
    
    aw_info = {
        'ip': args.ip,
        'username': args.username,
        'password': args.password
    }
    
    print("Initializing AirWave API connection...")
    aw = ArubaAirwave(aw_info, ssl_verify=False)
    
    if args.dry_run:
        print("\n--- [DRY RUN] folder_list.xml ---")
        folder_xml = aw.command(apiPath='/folder_list.xml')
        if folder_xml:
            print(folder_xml[:500] + "\n... (truncated)")
        else:
            print("Failed to get folder list")

        print("\n--- [DRY RUN] ap_list.xml ---")
        ap_xml = aw.command(apiPath='/ap_list.xml')
        if ap_xml:
            print(ap_xml[:1000] + "\n... (truncated)")
        else:
            print("Failed to get AP list")
            
        print("\nDry run complete. Exiting without generating mRemoteNG XML.")
        return

    print("Fetching folder list from AirWave... (this might take a moment)")
    folder_xml = aw.get_folder_list()
    if not folder_xml:
        print("Error: Received empty response for folder list.")
        return
        
    folders = parse_folders(folder_xml)
    print(f"Parsed {len(folders)} folders.")
    
    print("Fetching device list from AirWave... (this might take some time depending on number of devices)")
    # ap_list.xml provides a clean list of APs with their folder IDs and IPs
    ap_xml = aw.command(apiPath='/ap_list.xml')
    if not ap_xml:
        print("Error: Received empty response for AP list.")
        return
        
    devices = parse_devices(ap_xml)
    print(f"Parsed {len(devices)} devices.")
    
    print("Building folder hierarchy...")
    root_folders = build_tree(folders, devices)
    
    out_file = args.output
    create_mremoteng_xml(folders, root_folders, out_file, args.master_folder)
    print("Process complete.")

if __name__ == "__main__":
    main()
