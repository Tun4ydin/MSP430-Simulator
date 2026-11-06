try:
    import tkinter  # noqa: F401
except ImportError:
    raise SystemExit('tkinter bulunamadi. Tk destekli bir Python kullanin, ornegin: /usr/local/bin/python3 -m msp430sim')
from .gui import main

main()
