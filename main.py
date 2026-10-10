import os
import sys
import runpy

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    aerox_dir = os.path.join(current_dir, "AeroX")
    aerox_main = os.path.join(aerox_dir, "main.py")

    os.chdir(aerox_dir)
    if aerox_dir not in sys.path:
        sys.path.insert(0, aerox_dir)

    runpy.run_path(aerox_main, run_name="__main__")
