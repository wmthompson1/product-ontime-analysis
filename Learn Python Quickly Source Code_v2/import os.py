import os

def find_venv(start_path='.'):
    for root, dirs, files in os.walk(start_path):
        if '.venv' in dirs:
            return os.path.join(root, '.venv')
    return None

venv_path = find_venv()
if venv_path:
    print(f"Found .venv at: {venv_path}")
else:
    print(".venv not found.")