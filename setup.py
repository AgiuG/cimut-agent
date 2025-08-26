import os
import shutil
import sys
import subprocess
import platform

def create_agent_executable():
    try:
        import PyInstaller
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--console",
        "--name", f"cimut_agent_{platform.system().lower()}",
        "local_agent.py"
    ]
    
    subprocess.run(cmd)
    print("Agent executable created in dist/ folder")

if __name__ == "__main__":
    create_agent_executable()
