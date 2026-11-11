# Extras and Utilities

This directory contains utility scripts that complement the main `export_to_mremoteng.py` tool.

## Available Utilities

| Script | Documentation | Description |
| :--- | :--- | :--- |
| [`extract_csv.py`](extract_csv.py) | [extract_csv.md](extract_csv.md) | Parses the generated mRemoteNG XML file and exports a flat CSV inventory containing hostname, category, model, serial number, and IP address. |
| [`airwave_ap_detail.py`](airwave_ap_detail.py) | [airwave_ap_detail.md](airwave_ap_detail.md) | Queries Aruba AirWave directly for a specific AP or network device ID and outputs/saves the raw `ap_detail.xml` XML payload. |
