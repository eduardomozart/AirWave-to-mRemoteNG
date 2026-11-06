# Exporting mRemoteNG XML to CSV

This guide explains how to extract a flat CSV inventory of network devices from an mRemoteNG XML file using the `extract_csv.py` script located in the `extras/` directory.

## Overview

When `export_to_mremoteng.py` generates an XML file for mRemoteNG, devices are organized hierarchically as `<Node Type="Connection" ... />` elements. The `extract_csv.py` script parses this XML file and outputs a clean, tabular CSV file containing device details, categorizations, and network addressing.

## Supported Arguments

| Argument | Short | Description | Default |
| :--- | :---: | :--- | :--- |
| `--input` | `-i` | Input mRemoteNG XML file path | `mRemoteNG_AirWave.xml` |
| `--output` | `-o` | Output CSV file path | `mRemoteNG_AirWave.csv` |

## Output Columns

The exported CSV file includes the following columns:

| Column | Description | Source in XML |
| :--- | :--- | :--- |
| `hostname` | The device name/hostname | `Name` attribute |
| `category` | The device classification | Determined by hostname prefix or description |
| `model` | Hardware model (including manufacturer if present) | Parsed from `Descr` attribute |
| `serial_number` | Device serial number (S/N) | Parsed from `(S/N: ...)` in `Descr` attribute |
| `ip_address` | Device management IPv4 address | `Hostname` attribute |

### Category Mapping Logic

The device category is determined using the following hierarchy:
- If hostname starts with `ST` or `SW`: **`Switch`**
- If hostname starts with `AP`: **`Access Point (AP)`**
- If hostname starts with `MC`: **`Mobility Controller`**
- If hostname starts with `MM`: **`Mobility Master`**
- If description contains `switch` (case-insensitive): **`Switch`**
- Otherwise: **`Other`**

## Usage

### Default Execution
Run the script using the default file paths (`mRemoteNG_AirWave.xml` -> `mRemoteNG_AirWave.csv`):

```bash
python extras/extract_csv.py
```

### Custom Input and Output Paths
Specify custom XML input and CSV output file paths using `-i` / `--input` and `-o` / `--output`:

```bash
python extras/extract_csv.py -i my_connections.xml -o inventory.csv
```

The output file is encoded in UTF-8 with BOM (`utf-8-sig`) for compatibility with Microsoft Excel.
