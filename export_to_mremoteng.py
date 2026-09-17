import xml.etree.ElementTree as ET
from pyairwave.awapi import ArubaAirwave
import urllib3
import os
import argparse
import sys
import uuid

urllib3.disable_warnings()

VERSION = "DEV_BUILD"

def parse_args():
    """
    Auxiliary function to handle command-line arguments.
    """
    if '/?' in sys.argv:
        sys.argv[sys.argv.index('/?')] = '-h'

    parser = argparse.ArgumentParser(description=f"Export AirWave switches to mRemoteNG XML format. (Version: {VERSION})")
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}')
    parser.add_argument('-i', '--ip', required=True, help="AirWave Server IP or Hostname")
    parser.add_argument('-u', '--username', required=True, help="AirWave API Username")
    parser.add_argument('-p', '--password', required=True, help="AirWave API Password")
    parser.add_argument('-o', '--output', default="mRemoteNG_AirWave.xml", help="Output XML file name (default: mRemoteNG_AirWave.xml)")
    parser.add_argument('-f', '--airwave-folder', action='append', help="Filter by AirWave folder name (recursive). Can be specified multiple times or comma-separated.")
    parser.add_argument('-t', '--dry-run', action='store_true', help="Only test the AirWave connection and print raw XML fields (does not create an XML file)")
    parser.add_argument('-d', '--device-category', action='append', help="Filter devices by category. Can be specified multiple times or comma-separated.")
    parser.add_argument('-m', '--model', action='append', help="Filter devices by model. Can be specified multiple times or comma-separated.")
    try:
        args = parser.parse_args()
    except SystemExit:
        print("\nError: Missing required arguments. Please provide --ip, --username, and --password.")
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
        if name and name.strip().lower() == "top":
            continue
            
        parent_id = folder_el.findtext('parent_id')
        if fid:
            folders[fid] = {
                'name': name or "Unknown Folder", 
                'parent_id': parent_id, 
                'subfolders': [], 
                'devices': []
            }
    return folders

def parse_devices(xml_data, device_categories=None, models=None):
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
        if name and name.strip().startswith("(id:"):
            continue
            
        # IP could be in <lan_ip>, <ip>, or <remote_lan_ip>
        ip = ap_el.findtext('lan_ip') or ap_el.findtext('ip') or ap_el.findtext('remote_lan_ip') or ""
        
        # folder ID is typically an attribute in <folder id="...">
        folder_id = None
        folder_el = ap_el.find('folder')
        if folder_el is not None:
            folder_id = folder_el.get('id')
                
        device_category = ap_el.findtext('device_category') or ""
        model = ap_el.findtext('model') or ""
        
        # If filters are provided, check if either matches. Otherwise include all.
        if device_categories or models:
            is_match = False
            
            if device_categories and device_category:
                for cat in device_categories:
                    if cat.strip().lower() in device_category.lower():
                        is_match = True
                        break
                        
            if not is_match and models and model:
                for m in models:
                    if m.strip().lower() in model.lower():
                        is_match = True
                        break
                        
            if not is_match:
                continue
            
        serial_number = ap_el.findtext('serial_number') or ""
        devices.append({'name': name, 'ip': ip, 'folder_id': folder_id, 'model': model, 'serial_number': serial_number})
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

def create_mremoteng_xml(folders, root_folders, out_path="mRemoteNG_AirWave.xml"):
    """
    Generates mRemoteNG compatible XML file.
    """
    ET.register_namespace('mrng', 'http://mremoteng.org')
    root = ET.Element("{http://mremoteng.org}Connections", 
                      Name="Connections", 
                      Export="false",
                      EncryptionEngine="AES",
                      BlockCipherMode="GCM",
                      KdfIterations="1000",
                      FullFileEncryption="false",
                      Protected="zjEfDtvs6NSdcjGiMNojrC9xfCJPE1VXBPJbqqAMBxKn+yKU4FCwZkvhnUSG/wb5+N10GTtNpU2XaZ8rIul+8gQK",
                      ConfVersion="2.6")
    
    def add_node(parent_el, folder_id):
        fdata = folders[folder_id]
        container = ET.SubElement(parent_el, "Node", 
                                  Name=fdata['name'], 
                                  Type="Container", 
                                  Id=str(uuid.uuid4()),
                                  Descr="",
                                  Icon="mRemoteNG",
                                  Panel="General",
                                  Expanded="false",
                                  Protocol="SSH2",
                                  Port="22",
                                  PuttySession="Default Settings")
        
        # Add subfolders recursively (alphabetically sorted)
        for sub_id in sorted(fdata['subfolders'], key=lambda x: folders[x]['name'].lower()):
            add_node(container, sub_id)
            
        # Add devices
        for dev in fdata['devices']:
            dev_name = dev['name'] or dev['ip'] or "Unknown Device"
            descr = dev['model'].strip()
            if dev['serial_number']:
                descr += f" (S/N: {dev['serial_number']})"
            # Some essential properties to prevent mRemoteNG from complaining
            ET.SubElement(container, "Node", 
                          Name=dev_name, 
                          Type="Connection", 
                          Id=str(uuid.uuid4()),
                          Descr=descr,
                          Icon="mRemoteNG",
                          Panel="General",
                          Hostname=dev['ip'] or "", 
                          Protocol="SSH2", 
                          Port="22",
                          PuttySession="Default Settings",
                          Username="",
                          Domain="",
                          Password="",
                          MacAddress="",
                          UserField="")
                          
        # If the folder has no devices and no subfolders, remove it
        if len(container) == 0:
            parent_el.remove(container)

    for rf in sorted(root_folders, key=lambda x: folders[x]['name'].lower() if x in folders else x):
        add_node(root, rf)
        
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ", level=0)
    xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(xml_str)
        
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
            print(folder_xml)
        else:
            print("Failed to get folder list")

        print("\n--- [DRY RUN] ap_list.xml ---")
        ap_xml = aw.command(apiPath='/ap_list.xml')
        if ap_xml:
            print(ap_xml)
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
        
    device_categories = []
    if args.device_category:
        for item in args.device_category:
            device_categories.extend([cat.strip() for cat in item.split(',') if cat.strip()])

    models = []
    if args.model:
        for item in args.model:
            models.extend([m.strip() for m in item.split(',') if m.strip()])

    devices = parse_devices(ap_xml, device_categories if device_categories else None, models if models else None)
    print(f"Parsed {len(devices)} devices.")
    
    print("Building folder hierarchy...")
    root_folders = build_tree(folders, devices)
    
    airwave_folders = []
    if args.airwave_folder:
        for item in args.airwave_folder:
            airwave_folders.extend([f.strip() for f in item.split(',') if f.strip()])
            
    if airwave_folders:
        filtered_roots = []
        for fid, fdata in folders.items():
            # Check if this folder's name matches any of the requested folders (case-insensitive)
            for awf in airwave_folders:
                if awf.lower() == fdata['name'].lower():
                    filtered_roots.append(fid)
                    break
        if not filtered_roots:
            print("Warning: None of the specified AirWave folders were found.")
            return
        root_folders = filtered_roots
    
    out_file = args.output
    create_mremoteng_xml(folders, root_folders, out_file)
    print("Process complete.")

if __name__ == "__main__":
    main()
