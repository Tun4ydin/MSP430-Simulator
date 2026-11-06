#!/usr/bin/env python3
"""MSP430 Simulator single-command launcher."""
import os
import sys
from pathlib import Path

# Proje dizinini sys.path'e ekle
ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from msp430sim.cli import find_tk_python, run_cli


def main():
    code, result = run_cli(sys.argv[1:])
    if code != -1:
        if result:
            print(result)
        sys.exit(code)

    initial_file = result
    try:
        import tkinter  # noqa: F401
    except ImportError:
        tk_py = find_tk_python()
        if tk_py and tk_py != sys.executable:
            os.execv(tk_py, [tk_py, str(ROOT / 'run.py'), *sys.argv[1:]])

        sys.exit(
            'Hata: Bu Python surumunde Tkinter bulunamadi.\n'
            'Cozum:\n'
            '  - macOS: brew install python-tk veya /usr/local/bin/python3 run.py\n'
            '  - Linux: sudo apt-get install python3-tk\n'
            '  - CLI modu: python3 run.py --cli <dosya.asm>'
        )

    from msp430sim.gui import main as gui_main
    gui_main(initial_file=initial_file)


if __name__ == '__main__':
    main()
