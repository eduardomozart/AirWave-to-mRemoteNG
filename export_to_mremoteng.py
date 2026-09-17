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
    parser.add_argument('-i', '--ip', required=True, help="AirWave Server IP or Hostname")
    parser.add_argument('-u', '--username', required=True, help="AirWave API Username")
    parser.add_argument('-p', '--password', required=True, help="AirWave API Password")
    parser.add_argument('-o', '--output', default="mRemoteNG_AirWave.xml", help="Output XML file name (default: mRemoteNG_AirWave.xml)")
    parser.add_argument('-f', '--airwave-folder', action='append', help="Filter by AirWave folder name (recursive). Can be specified multiple times.")
    parser.add_argument('-c', '--device-category', action='append', help="Filter devices by category (e.g. switch, thin_ap, controller). Can be specified multiple times.")
    parser.add_argument('-m', '--model', action='append', help="Filter devices by model. Can be specified multiple times.")
    parser.add_argument('-d', '--debug', action='store_true', help="Print raw XML payloads from AirWave API to the console before generating the mRemoteNG file.")
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}')
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
    total_devices = 0
    for ap_el in root.iter('ap'):
        total_devices += 1
        name = ap_el.findtext('name')
        if name and name.strip().startswith("(id:"):
            continue
            
        # IP could be in <lan_ip>, <ip>, or <remote_lan_ip>
        ip = ap_el.findtext('lan_ip') or ap_el.findtext('ip') or ap_el.findtext('remote_lan_ip') or ""
        if not ip:
            continue
        
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
    return devices, total_devices

def flatten_folders_by_category(folders, devices, device_categories):
    """
    Removes folders that exactly match the provided device categories, EXCEPT 
    when a parent folder contains multiple categories (e.g. both 'Switch' and 'Access Point').
    Reassigns flattened devices and subfolders to the nearest kept parent folder.
    """
    if not device_categories:
        return

    candidate_folders = set()
    
    # Identify all folders whose names exactly match the passed-in device categories (case-insensitive)
    for fid, fdata in folders.items():
        name_lower = fdata['name'].strip().lower()
        for cat in device_categories:
            if cat.lower() == name_lower:
                candidate_folders.add(fid)
                break
                
    if not candidate_folders:
        return

    # Group these candidate folders by their parent_id
    parent_to_candidates = {}
    for fid in candidate_folders:
        pid = folders[fid].get('parent_id')
        if pid not in parent_to_candidates:
            parent_to_candidates[pid] = []
        parent_to_candidates[pid].append(fid)

    folders_to_remove = set()
    
    # Only flag for removal if it's the ONLY matched category folder under that parent
    for pid, sibling_fids in parent_to_candidates.items():
        if len(sibling_fids) == 1:
            folders_to_remove.add(sibling_fids[0])
        # If len >= 2, we leave them alone so they don't merge into a mess

    if not folders_to_remove:
        return

    def get_kept_parent(fid):
        # Climbs the folder tree until it finds an ancestor that isn't flagged for removal
        curr = fid
        while curr in folders_to_remove:
            p = folders[curr].get('parent_id')
            if not p or p not in folders:
                return None
            curr = p
        return curr

    # Reassign devices from the removed folder to its surviving parent
    for dev in devices:
        if dev['folder_id'] in folders_to_remove:
            dev['folder_id'] = get_kept_parent(dev['folder_id'])

    # Reassign orphan subfolders to the surviving parent
    for fid, fdata in list(folders.items()):
        if fid not in folders_to_remove and fdata['parent_id'] in folders_to_remove:
            fdata['parent_id'] = get_kept_parent(fdata['parent_id'])

    # Remove bypassed folders entirely so they don't get imported
    for fid in folders_to_remove:
        del folders[fid]

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
    
    # Full set of default attributes expected by mRemoteNG's deserializer.
    # Omitting any of these can cause a NullReferenceException on import.
    DEFAULT_PROPS = dict(
        Username="", Domain="", Password="", Hostname="",
        Protocol="SSH2", PuttySession="Default Settings", Port="22",
        ConnectToConsole="false", UseCredSsp="true", RenderingEngine="IE",
        ICAEncryptionStrength="EncrBasic", RDPAuthenticationLevel="NoAuth",
        RDPMinutesToIdleTimeout="0", RDPAlertIdleTimeout="false",
        LoadBalanceInfo="", Colors="Colors16Bit", Resolution="FitToWindow",
        AutomaticResize="true", DisplayWallpaper="false", DisplayThemes="false",
        EnableFontSmoothing="false", EnableDesktopComposition="false",
        CacheBitmaps="false", RedirectDiskDrives="false", RedirectPorts="false",
        RedirectPrinters="false", RedirectSmartCards="false",
        RedirectSound="DoNotPlay", SoundQuality="Dynamic", RedirectKeys="false",
        Connected="false", PreExtApp="", PostExtApp="", MacAddress="",
        UserField="", ExtApp="",
        VNCCompression="CompNone", VNCEncoding="EncHextile",
        VNCAuthMode="AuthVNC", VNCProxyType="ProxyNone", VNCProxyIP="",
        VNCProxyPort="0", VNCProxyUsername="", VNCProxyPassword="",
        VNCColors="ColNormal", VNCSmartSizeMode="SmartSAspect", VNCViewOnly="false",
        RDGatewayUsageMethod="Never", RDGatewayHostname="",
        RDGatewayUseConnectionCredentials="Yes", RDGatewayUsername="",
        RDGatewayPassword="", RDGatewayDomain="",
        InheritCacheBitmaps="false", InheritColors="false",
        InheritDescription="false", InheritDisplayThemes="false",
        InheritDisplayWallpaper="false", InheritEnableFontSmoothing="false",
        InheritEnableDesktopComposition="false", InheritDomain="false",
        InheritIcon="false", InheritPanel="false", InheritPassword="false",
        InheritPort="false", InheritProtocol="false", InheritPuttySession="false",
        InheritRedirectDiskDrives="false", InheritRedirectKeys="false",
        InheritRedirectPorts="false", InheritRedirectPrinters="false",
        InheritRedirectSmartCards="false", InheritRedirectSound="false",
        InheritSoundQuality="false", InheritResolution="false",
        InheritAutomaticResize="false", InheritUseConsoleSession="false",
        InheritUseCredSsp="false", InheritRenderingEngine="false",
        InheritUsername="false", InheritICAEncryptionStrength="false",
        InheritRDPAuthenticationLevel="false",
        InheritRDPMinutesToIdleTimeout="false", InheritRDPAlertIdleTimeout="false",
        InheritLoadBalanceInfo="false", InheritPreExtApp="false",
        InheritPostExtApp="false", InheritMacAddress="false",
        InheritUserField="false", InheritExtApp="false",
        InheritVNCCompression="false", InheritVNCEncoding="false",
        InheritVNCAuthMode="false", InheritVNCProxyType="false",
        InheritVNCProxyIP="false", InheritVNCProxyPort="false",
        InheritVNCProxyUsername="false", InheritVNCProxyPassword="false",
        InheritVNCColors="false", InheritVNCSmartSizeMode="false",
        InheritVNCViewOnly="false", InheritRDGatewayUsageMethod="false",
        InheritRDGatewayHostname="false",
        InheritRDGatewayUseConnectionCredentials="false",
        InheritRDGatewayUsername="false", InheritRDGatewayPassword="false",
        InheritRDGatewayDomain="false",
    )

    def add_node(parent_el, folder_id):
        fdata = folders[folder_id]
        attrs = dict(DEFAULT_PROPS)
        attrs.update(
            Name=fdata['name'],
            Type="Container",
            Id=str(uuid.uuid4()),
            Descr="",
            Icon="mRemoteNG",
            Panel="General",
            Expanded="false",
            Protocol="SSH2",
            Port="22",
            PuttySession="Default Settings",
        )
        container = ET.SubElement(parent_el, "Node", **attrs)
        
        # Add subfolders recursively (alphabetically sorted)
        for sub_id in sorted(fdata['subfolders'], key=lambda x: folders[x]['name'].lower()):
            add_node(container, sub_id)
            
        # Add devices (alphabetically sorted)
        for dev in sorted(fdata['devices'], key=lambda x: (x['name'] or x['ip'] or "").lower()):
            dev_name = dev['name'] or dev['ip'] or "Unknown Device"
            descr = dev['model'].strip()
            if dev['serial_number']:
                descr += f" (S/N: {dev['serial_number'].strip()})"
            dev_attrs = dict(DEFAULT_PROPS)
            dev_attrs.update(
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
            )
            ET.SubElement(container, "Node", **dev_attrs)
                          
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
    
    print("Fetching folder list from AirWave... (this might take a moment)")
    folder_xml = aw.get_folder_list()
    if not folder_xml:
        print("Error: Received empty response for folder list.")
        return
        
    if args.debug:
        print("\n--- [DEBUG] folder_list.xml ---")
        print(folder_xml)
        
    folders = parse_folders(folder_xml)
    print(f"Parsed {len(folders)} folders.")
    
    print("Fetching device list from AirWave... (this might take some time depending on number of devices)")
    # ap_list.xml provides a clean list of APs with their folder IDs and IPs
    ap_xml = aw.command(apiPath='/ap_list.xml')
    if not ap_xml:
        print("Error: Received empty response for AP list.")
        return
        
    if args.debug:
        print("\n--- [DEBUG] ap_list.xml ---")
        print(ap_xml)
        
    device_categories = []
    if args.device_category:
        for item in args.device_category:
            device_categories.append(item.strip())

    models = []
    if args.model:
        for item in args.model:
            models.append(item.strip())

    devices, total_devices = parse_devices(ap_xml, device_categories if device_categories else None, models if models else None)
    print(f"Parsed {len(devices)} devices (out of {total_devices} total devices in AirWave).")
    
    flatten_folders_by_category(folders, devices, device_categories)
    
    print("Building folder hierarchy...")
    root_folders = build_tree(folders, devices)
    
    airwave_folders = []
    if args.airwave_folder:
        for item in args.airwave_folder:
            airwave_folders.append(item.strip())
            
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
