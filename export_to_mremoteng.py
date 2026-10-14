import xml.etree.ElementTree as ET
from airwaveapiclient import AirWaveAPIClient, APList, FolderList
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
    parser.add_argument('-f', '--airwave-folder', action='append', help="Filter by AirWave folder name or ID (recursive). Can be specified multiple times.")
    parser.add_argument('-l', '--flatten-folder', action='append', help="Flatten specific folder names (e.g. 'Switch', 'Access Point') by removing them from the mRemoteNG hierarchy and reassigning their devices to the parent folder. Can be specified multiple times.")
    parser.add_argument('-c', '--device-category', action='append', help="Filter devices by category (e.g. switch, thin_ap, controller). Can be specified multiple times.")
    parser.add_argument('-m', '--model', action='append', help="Filter devices by model. Can be specified multiple times.")
    parser.add_argument('-d', '--debug', action='store_true', help="Print raw XML payloads from AirWave API to the console before generating the mRemoteNG file.")
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}')
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 0:
            raise
        print("\nError: Missing required arguments. Please provide --ip, --username, and --password.")
        sys.exit(1)
        
    return args

def parse_folders(xml_data):
    """
    Parses folder_list.xml to extract folders and build a hierarchy using FolderList.
    Returns:
        tuple: (folders, fl)
            folders (dict): {folder_id: {'name': folder_name, 'parent_id': parent_id, 'subfolders': [], 'devices': [], 'folder_path': folder_path}}
            fl (FolderList or None): FolderList object
    """
    try:
        fl = xml_data if isinstance(xml_data, FolderList) else FolderList(xml_data)
    except Exception as e:
        print(f"Error parsing folder list XML: {e}")
        return {}, None

    folders = {}
    all_names = {}
    all_parents = {}
    for node in fl:
        fid = str(node.get('@id') or node.get('id') or '').strip()
        fname = str(node.get('name') or '').strip()
        if fid:
            all_names[fid] = fname
            pid = str(node.get('parent_id') or node.get('parent') or '').strip()
            all_parents[fid] = pid if pid and pid != '0' else None

    for fid, name in all_names.items():
        if name and name.lower() == "top":
            continue
        folders[fid] = {
            'name': name or "Unknown Folder", 
            'parent_id': all_parents.get(fid), 
            'subfolders': [], 
            'devices': []
        }

    # Precompute folder_path breadcrumbs for each folder
    for fid, fdata in folders.items():
        path_names = [fdata['name']]
        curr = fdata['parent_id']
        visited = {fid}
        while curr and curr not in visited:
            visited.add(curr)
            if curr in all_names:
                path_names.append(all_names[curr])
            curr = all_parents.get(curr)
        path_names.reverse()
        fdata['folder_path'] = " > ".join(path_names)

    return folders, fl

def parse_devices(xml_data, device_categories=None, models=None):
    """
    Parses ap_list.xml to extract devices (APs) using APList.
    Returns a list of dicts: [{'name': ..., 'ip': ..., 'folder_id': ...}, ...]
    """
    try:
        ap_list = xml_data if isinstance(xml_data, APList) else APList(xml_data)
    except Exception as e:
        print(f"Error parsing AP list XML: {e}")
        return [], 0

    devices = []
    total_devices = len(ap_list)
    for ap in ap_list:
        name = ap.get('name')
        if not name or str(name).strip().startswith("(id:"):
            continue

        ip = ap.get('lan_ip') or ap.get('ip') or ap.get('remote_lan_ip') or ""
        if not ip:
            continue

        folder_id = None
        folder_field = ap.get('folder')
        if isinstance(folder_field, dict):
            folder_id = folder_field.get('@id') or folder_field.get('id')
        elif folder_field:
            folder_id = str(folder_field)
        if not folder_id:
            folder_id = ap.get('@folder_id') or ap.get('folder_id') or ap.get('ap_folder_id')

        device_category = ap.get('device_category') or ""
        model_field = ap.get('model') or ""
        if isinstance(model_field, dict):
            model = model_field.get('#text') or model_field.get('name') or ""
        else:
            model = str(model_field)
        model = model.strip()

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

        serial_number = ap.get('serial_number') or ""
        if isinstance(serial_number, dict):
            serial_number = serial_number.get('#text') or ""

        devices.append({
            'name': name,
            'ip': ip,
            'folder_id': str(folder_id) if folder_id else None,
            'model': model,
            'serial_number': str(serial_number)
        })

    return devices, total_devices

def flatten_folders_by_name(folders, devices, flatten_folders):
    """
    Removes folders whose names contain any of the provided strings in flatten_folders
    from the mRemoteNG hierarchy, EXCEPT when a parent folder contains multiple such 
    folders (e.g. both 'Switch' and 'Access Point').
    Reassigns flattened devices and subfolders to the nearest kept parent folder.
    """
    if not flatten_folders:
        return

    candidate_folders = set()
    
    # Identify all folders whose names contain the passed-in strings (case-insensitive)
    for fid, fdata in folders.items():
        name_lower = fdata['name'].strip().lower()
        for folder_name in flatten_folders:
            if folder_name.lower() in name_lower:
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
            # Note: mRemoteNG stable (v1.76.20) fails to import entries where properties
            # like 'Descr' start with a space. This bug is fixed in the current Nightly, 
            # but we strip() the string here to ensure compatibility with stable releases.
            descr = dev['model'].strip()
            if dev['serial_number']:
                descr += f" (S/N: {dev['serial_number']})"
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
    
    ip = args.ip.strip()
    url = ip if ip.startswith(('http://', 'https://')) else f"https://{ip}"
    
    print("Initializing AirWave API connection...")
    client = AirWaveAPIClient(username=args.username, password=args.password, url=url)
    
    try:
        login_res = client.login()
        if login_res.status_code != 200:
            print(f"Error: AirWave login failed with status code {login_res.status_code}.")
            return
    except Exception as e:
        print(f"Error connecting to AirWave: {e}")
        return

    try:
        print("Fetching folder list from AirWave... (this might take a moment)")
        folder_resp = client.folder_list()
        folder_xml = folder_resp.text if folder_resp is not None else ""
        if not folder_xml:
            print("Error: Received empty response for folder list.")
            return
            
        if args.debug:
            print("\n--- [DEBUG] folder_list.xml ---")
            print(folder_xml)
            
        folders, fl = parse_folders(folder_xml)
        print(f"Parsed {len(folders)} folders.")
        
        print("Fetching device list from AirWave... (this might take some time depending on number of devices)")
        # ap_list.xml provides a clean list of APs with their folder IDs and IPs
        ap_resp = client.ap_list()
        ap_xml = ap_resp.text if ap_resp is not None else ""
        if not ap_xml:
            print("Error: Received empty response for AP list.")
            return
            
        if args.debug:
            print("\n--- [DEBUG] ap_list.xml ---")
            print(ap_xml)
            
        devices, total_devices = parse_devices(ap_xml, args.device_category, args.model)
        print(f"Parsed {len(devices)} devices (out of {total_devices} total devices in AirWave).")
        
        if args.flatten_folder:
            flatten_folders_by_name(folders, devices, args.flatten_folder)
        
        print("Building folder hierarchy...")
        root_folders = build_tree(folders, devices)
        
        if args.airwave_folder:
            filtered_roots = []
            matched_ids = set()
            for awf in args.airwave_folder:
                target = str(awf).strip()
                # 1. Search by ID via fl.search
                match_node = fl.search(target) if fl is not None else None
                if match_node:
                    mfid = str(match_node.get('@id') or match_node.get('id') or '').strip()
                    if mfid and mfid in folders:
                        matched_ids.add(mfid)

                # 2. Match against exact name or breadcrumb folder_path
                target_lower = target.lower()
                for fid, fdata in folders.items():
                    fname = fdata['name'].lower()
                    fpath = fdata.get('folder_path', '').lower()
                    if target_lower == fname or target_lower in fpath:
                        matched_ids.add(fid)

            # Pick the topmost matched folders as root_folders
            for fid in matched_ids:
                if fid in folders:
                    pid = folders[fid].get('parent_id')
                    if pid not in matched_ids:
                        filtered_roots.append(fid)

            if not filtered_roots:
                print("Warning: None of the specified AirWave folders were found.")
                return
            root_folders = filtered_roots
        
        out_file = args.output
        create_mremoteng_xml(folders, root_folders, out_file)
        print("Process complete.")
    finally:
        try:
            client.logout()
        except Exception:
            pass

if __name__ == "__main__":
    main()
