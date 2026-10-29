"""PyInstaller entry point, including the optional private phone gateway."""
import sys
from interface.desktop import main
from interface.phone_server import main as phone_main

if __name__ == '__main__':
    if '--phone-gateway' in sys.argv:
        sys.argv.remove('--phone-gateway')
        phone_main()
    else:
        main()
