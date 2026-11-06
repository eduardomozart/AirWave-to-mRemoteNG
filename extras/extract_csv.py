import xml.etree.ElementTree as ET
import csv
import re
import os
import sys
import argparse

def parse_args():
    """
    Parses command-line arguments for input XML and output CSV file paths.
    """
    if '/?' in sys.argv:
        sys.argv[sys.argv.index('/?')] = '-h'

    parser = argparse.ArgumentParser(description="Extract network devices from an mRemoteNG XML file to CSV.")
    parser.add_argument('-i', '--input', default="mRemoteNG_AirWave.xml", help="Input mRemoteNG XML file path (default: mRemoteNG_AirWave.xml)")
    parser.add_argument('-o', '--output', default="mRemoteNG_AirWave.csv", help="Output CSV file path (default: mRemoteNG_AirWave.csv)")
    return parser.parse_args()

def extract_devices_to_csv(xml_path="mRemoteNG_AirWave.xml", csv_path="mRemoteNG_AirWave.csv"):
    """
    Extracts network devices from an mRemoteNG XML file and exports them to CSV.
    """
    if not os.path.exists(xml_path):
        print(f"Error: Input file '{xml_path}' does not exist.")
        return 1

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML file '{xml_path}': {e}")
        return 1

    # Pattern to extract model and optional serial number from the Descr attribute:
    # e.g., "Aruba AP 535 (S/N: VNPNK9W6GZ)" or "8360  Switch (S/N: SG59L5L05H)"
    pattern = re.compile(r'^(.*?)(?:\s*\(S/N:\s*([^)]*)\))?$')

    records = []

    for elem in root.iter():
        if elem.tag.endswith('Node') and elem.get('Type') == 'Connection':
            hostname = elem.get('Name', '').strip()
            ip_addr = elem.get('Hostname', '').strip()
            descr = elem.get('Descr', '').strip()

            match = pattern.match(descr)
            if match:
                model = match.group(1).strip()
                serial_number = match.group(2).strip() if match.group(2) else ''
            else:
                model = descr
                serial_number = ''

            # Categorize devices based on prefix and description
            if hostname.startswith('ST') or hostname.startswith('SW'):
                category = 'Switch'
            elif hostname.startswith('AP'):
                category = 'Access Point (AP)'
            elif hostname.startswith('MC'):
                category = 'Mobility Controller'
            elif hostname.startswith('MM'):
                category = 'Mobility Master'
            elif 'switch' in descr.lower():
                category = 'Switch'
            else:
                category = 'Other'

            records.append({
                'hostname': hostname,
                'category': category,
                'model': model,
                'serial_number': serial_number,
                'ip_address': ip_addr
            })

    fieldnames = ['hostname', 'category', 'model', 'serial_number', 'ip_address']
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
    except Exception as e:
        print(f"Error writing CSV file '{csv_path}': {e}")
        return 1

    print(f"Successfully exported {len(records)} devices to '{csv_path}'")
    return 0

def main():
    args = parse_args()
    return extract_devices_to_csv(xml_path=args.input, csv_path=args.output)

if __name__ == '__main__':
    sys.exit(main())
