# Querying AirWave AP Detail XML

This guide explains how to query an Aruba AirWave server and view or save the raw `ap_detail.xml` XML payload for a specific Access Point (AP) or network device using the `airwave_ap_detail.py` script located in the `extras/` directory.

## Overview

AirWave provides detailed hardware, radio, interface, and operational data for individual devices via the `ap_detail.xml` API endpoint (`/api/ap_detail.xml?id=<AP_ID>`).

The `airwave_ap_detail.py` script allows you to query this endpoint for a given device ID, print the raw XML response to standard output (`stdout`), and save it to an XML file for troubleshooting, inspection, or development.

## Supported Arguments

| Argument | Short | Description | Default |
| :--- | :---: | :--- | :--- |
| `ap_id` | *(positional)* | The AirWave device/AP ID to query (**Required**) | *(None)* |
| `--url` | | AirWave server URL or IP address (e.g., `https://10.0.0.5` or `10.0.0.5`) | `https://airwave` |
| `--username` | `-u` | AirWave API username (optional; falls back to `AIRWAVE_USER` env var or prompt) | *(prompt)* |
| `--password` | `-p` | AirWave API password (optional; falls back to `AIRWAVE_PASS` env var or prompt) | *(prompt)* |
| `--out` | `-o` | Output XML file path to save payload (optional; if omitted, XML is only printed to stdout) | *(None)* |

## Authentication

Credentials can be supplied in three ways (in order of precedence):
1. **Command-line arguments**: `-u` / `--username` and `-p` / `--password`
2. **Environment variables**: `AIRWAVE_USER` and `AIRWAVE_PASS`
3. **Interactive prompt**: The script will securely prompt for the username and password (with masked input) if not provided.

## Usage

> [!IMPORTANT]
> The `ap_id` argument is required. If omitted, the script exits with an error.

### Basic Execution
Query a specific device ID (e.g., `1024`) with default URL (`https://airwave`):

```bash
python extras/airwave_ap_detail.py 1024
```

### Specifying Server URL
Query a specific device ID (e.g., `1024`) on your AirWave server:

```bash
python extras/airwave_ap_detail.py 1024 --url https://10.0.0.5
```

### Specifying Custom Output File Path
Save the XML response to a specific destination file using `-o` / `--out`:

```bash
python extras/airwave_ap_detail.py 1024 --url https://10.0.0.5 -o ap_1024_backup.xml
```

### Using Environment Variables for Automation
Set environment variables for unattended scripts or automated workflows:

**PowerShell:**
```powershell
$env:AIRWAVE_USER = "admin"
$env:AIRWAVE_PASS = "SecretPass123"
python extras/airwave_ap_detail.py 1024 --url https://10.0.0.5
```

**Linux / macOS (Bash):**
```bash
export AIRWAVE_USER="admin"
export AIRWAVE_PASS="SecretPass123"
python extras/airwave_ap_detail.py 1024 --url https://10.0.0.5
```

**Windows CMD:**
```cmd
set AIRWAVE_USER=admin
set AIRWAVE_PASS=SecretPass123
python extras/airwave_ap_detail.py 1024 --url https://10.0.0.5
```

### Output and Redirection
Informational messages and HTTP status codes are written to `stderr`, while the raw XML content is written to `stdout`. This allows piping the XML output directly to XML processors or other CLI utilities:

```bash
python extras/airwave_ap_detail.py 1024 --url https://10.0.0.5 > ap_1024.xml
```
