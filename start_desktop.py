from pathlib import Path
import subprocess
import sys
from tkinter import messagebox


base = Path(__file__).resolve().parent
launcher = base / 'desktop-app' / 'seeq.exe'
try:
    subprocess.Popen([str(launcher), sys.executable], cwd=base)
except OSError:
    messagebox.showerror('seeq', 'Não consegui abrir desktop-app\\seeq.exe. Mantenha as pastas do aplicativo juntas.')
