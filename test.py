import os
import sys

def get_current_working_directory():
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    return cwd

def get_script_dir():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # sets the sys._MEIPASS attribute to the path of the temporary directory.
        return os.getcwd()
    else:
        # If the application is run as a script, use the directory of the script file.
        print("Running as a script")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"script_dir: {script_dir}")
        return script_dir

script_dir = get_script_dir()
input ("Press Enter to continue...")


