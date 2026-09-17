# AirWave-to-mRemoteNG
A Python tool that extracts network device hierarchies (switches/APs) from the Aruba AirWave API and exports them into an mRemoteNG-compatible XML configuration.

## Binary Releases
Download the latest pre-compiled version from the **[Releases tab](../../releases)**.

## Requirements
If you are running the script from source, this script relies on the [pyairwave](https://github.com/AIOpsTiger/pyairwave) module for API interactions.

You can install it directly via `pip` from its GitHub repository:
```bash
pip install git+https://github.com/AIOpsTiger/pyairwave.git
```

## Usage
Run the script from the command line using the required arguments.

```powershell
python export_to_mremoteng.py --ip <AIRWAVE_IP> --username <USERNAME> --password <PASSWORD>
```

### Supported Arguments

| Argument | Short | Required | Description |
| :--- | :---: | :---: | :--- |
| `--ip` | `-i` | **Yes** | The IP address or Hostname of your Aruba AirWave server. |
| `--username` | `-u` | **Yes** | Your AirWave API Administrator username. |
| `--password` | `-p` | **Yes** | Your AirWave API Administrator password. |
| `--output` | `-o` | No | Custom filename for the output XML. (Default: `mRemoteNG_AirWave.xml`) |
| `--mremoteng-folder` | `-n` | No | Wraps all exported items in a root folder with this name (e.g., `"AirWave Sync"`). Highly recommended to make updating and deleting duplicates in mRemoteNG easier. |
| `--airwave-folder` | `-f` | No | Filter by AirWave folder name (recursive). Can be passed multiple times or comma-separated. Exports all folders by default. |
| `--device-category` | `-d` | No | Filter by `<device_category>` (e.g. `switch,thin_ap`). Can be passed multiple times (e.g. `-d switch -d thin_ap`) or comma-separated. Exports everything by default. |
| `--model` | `-m` | No | Filter by `<model>` (e.g. `AP 535`). Can be passed multiple times or comma-separated. |
| `--dry-run` | `-t` | No | Test mode: Only connects to AirWave and prints the raw XML output. It will *not* generate the mRemoteNG file. |
| `--version` | `-v` | No | Show program's version number and exit. |

### Example
```powershell
python export_to_mremoteng.py -i 10.0.0.5 -u admin -p SecretPass123 -n "AirWave Sync" -o my_network.xml
```

## How to Update mRemoteNG
Because mRemoteNG relies on unique GUIDs and **does not merge or update** existing imported entries natively, the best workflow for keeping your connections up to date is:
1. Run this script with the `-n "AirWave Sync"` argument.
2. In mRemoteNG, right-click and **delete** the old `AirWave Sync` folder.
3. Go to **File -> Import -> Import from File** and select your newly generated XML to bring in the fresh hierarchy.

## How to Create a Windows Binary

This repository includes a **GitHub Actions workflow** that automatically compiles a standalone `.exe` and creates a GitHub Release every time a new tag (e.g., `v1.0.0`) is pushed. 

If you prefer to compile it manually, you can easily create a standalone Windows `.exe` using [PyInstaller](https://pyinstaller.org/).

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Generate the executable:
```bash
pyinstaller --onefile export_to_mremoteng.py
```

3. The generated executable will be located in the `dist/` folder.
