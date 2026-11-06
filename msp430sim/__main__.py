"""MSP430 Simulator entry point."""
import os
import sys

from .cli import find_tk_python, run_cli


def entry_point():
    code, result = run_cli(sys.argv[1:])
    if code != -1:
        if result:
            print(result)
        sys.exit(code)

    # GUI baslatilacak
    initial_file = result
    try:
        import tkinter  # noqa: F401
    except ImportError:
        # Tkinter yoksa sistemdeki uygun Python'u bulup onunla calistir
        tk_py = find_tk_python()
        if tk_py and tk_py != sys.executable:
            os.execv(tk_py, [tk_py, '-m', 'msp430sim', *sys.argv[1:]])

        sys.exit(
            'Hata: Bu Python surumunde Tkinter bulunamadi.\n'
            'Cozum:\n'
            '  - macOS: brew install python-tk veya /usr/local/bin/python3 -m msp430sim\n'
            '  - Linux: sudo apt-get install python3-tk\n'
            '  - CLI modu: python3 -m msp430sim --cli <dosya.asm>'
        )

    from .gui import main
    main(initial_file=initial_file)


if __name__ == '__main__':
    entry_point()
