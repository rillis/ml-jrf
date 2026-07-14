from cfg import config

from pathlib import Path
import ast

def should_run(resource):
    file = Path(config.LOG_FILE_PATH)
    if not file.exists(): arr = []
    else:
        with open(file, 'r') as f:
            arr = ast.literal_eval(f.read())
    if resource in arr:
        if config.DEBUG: print(f'SKIP {resource}')
        return False
    arr.append(resource)
    arr = arr[-config.MAX_LOG_SIZE:]
    with open(file, 'w') as f:
        f.write(str(arr))
    return True