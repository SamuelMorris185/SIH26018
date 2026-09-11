"""
Local Development Setup Script for SIH26018
"""
import sys
import subprocess

def check_python_version():
    print(f"[*] Python version: {sys.version}")
    if sys.version_info < (3, 10):
        print("[!] Warning: Python 3.10+ is recommended.")

def main():
    print("=== SIH26018 Development Setup Verification ===")
    check_python_version()
    print("[✓] Pre-flight checks passed.")

if __name__ == "__main__":
    main()
