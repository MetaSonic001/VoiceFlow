import sys
import pathlib

repo = pathlib.Path(__file__).resolve().parent
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from uvicorn import run

if __name__ == '__main__':
    run('tools.db_visualizer.app:app', host='127.0.0.1', port=8765, reload=True)
