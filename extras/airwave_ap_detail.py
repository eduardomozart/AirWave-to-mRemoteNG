"""
Queries Aruba AirWave and prints/saves the raw XML of ap_detail.xml for an AP/device.

Usage:
    python extras/airwave_ap_detail.py <AP_ID> [--url https://airwave] [--out file.xml]

Credentials: Read from AIRWAVE_USER / AIRWAVE_PASS environment variables, command-line arguments, or prompted securely.
"""
import argparse
import getpass
import os
import sys
import urllib3
from airwaveapiclient import AirWaveAPIClient

urllib3.disable_warnings()


def parse_args():
    """
    Parses command-line arguments for querying ap_detail.xml from AirWave.
    """
    if '/?' in sys.argv:
        sys.argv[sys.argv.index('/?')] = '-h'

    p = argparse.ArgumentParser(
        description="Query AirWave and print/save the raw ap_detail.xml XML for an AP/device."
    )
    p.add_argument("ap_id", help="AirWave AP/device ID")
    p.add_argument("--url", default="https://airwave", help="AirWave server URL or IP address (default: https://airwave)")
    p.add_argument("-u", "--username", default=None, help="AirWave username (or set AIRWAVE_USER env var)")
    p.add_argument("-p", "--password", default=None, help="AirWave password (or set AIRWAVE_PASS env var)")
    p.add_argument("-o", "--out", default=None, help="Output file path to save XML (optional, prints to stdout by default)")
    return p.parse_args()


def main():
    args = parse_args()

    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    username = args.username or os.environ.get("AIRWAVE_USER") or input("AirWave username: ").strip()
    password = args.password or os.environ.get("AIRWAVE_PASS") or getpass.getpass(f"Password for {username}: ")

    client = AirWaveAPIClient(username=username, password=password, url=url, verify=False)
    
    try:
        login = client.login()
    except Exception as e:
        sys.exit(f"[ERROR] Failed to connect to AirWave: {e}")

    if login is None or getattr(login, "status_code", 0) >= 400:
        sys.exit(f"[ERROR] Login failed (HTTP {getattr(login, 'status_code', '?')}).")

    try:
        res = client.ap_detail(args.ap_id)
    finally:
        try:
            client.logout()
        except Exception:
            pass

    print(f"# GET {res.url} -> HTTP {res.status_code}\n", file=sys.stderr)
    print(res.text)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(res.text)
        print(f"\n# XML saved to: {os.path.abspath(args.out)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
