import json
import os
import platform
import subprocess
import psutil

def system_info():
    result = {"os": platform.platform(), "cpu": platform.processor() or platform.machine(), "ram_gib": round(psutil.virtual_memory().total/1024**3, 1), "gpus": [], "gpu_error": None}
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        if os.name == "nt":
            command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | ConvertTo-Json -Compress"]
            data = json.loads(subprocess.check_output(command, timeout=12, creationflags=flags, text=True))
            result["gpus"] = data if isinstance(data, list) else [data]
        else:
            result["gpus"] = [{"Name": "Windows GPU detection unavailable on this host"}]
    except Exception as exc: result["gpu_error"] = str(exc)
    return result
