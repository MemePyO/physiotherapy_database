import subprocess, sys, os
os.chdir(r"C:\Users\Admin\Desktop\patient_database_dashboard")
args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean", "--onefile", "--windowed",
    "--name", "PatientDatabase",
    "--add-data", "assets;assets",
    "--add-data", "version.py;.",
    "--hidden-import", "customtkinter",
    "--hidden-import", "PIL",
    "--hidden-import", "fitz",
    "--hidden-import", "openpyxl",
    "--hidden-import", "darkdetect",
    "main.py",
]
r = subprocess.run(args, capture_output=True, text=True)
open(r"C:\Users\Admin\AppData\Local\Temp\opencode\build3.log", "w", encoding="utf-8").write(r.stdout[-500:] + "\n---ERR---\n" + r.stderr[-500:])
print("RC:", r.returncode)
print("exists:", os.path.exists(r"C:\Users\Admin\Desktop\patient_database_dashboard\dist\PatientDatabase.exe"))
