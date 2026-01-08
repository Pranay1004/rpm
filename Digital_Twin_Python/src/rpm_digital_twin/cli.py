"""Small CLI entrypoint to launch the GUI for the RPM Digital Twin."""
from __future__ import annotations

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nogui', action='store_true', help="Don't launch GUI (reserved)")
    args = parser.parse_args()

    if args.nogui:
        print('No-GUI mode not implemented yet.')
        return

    # Lazy import to avoid PyQt import if not needed
    from rpm_digital_twin.gui.main_window import run_app
    run_app()


if __name__ == '__main__':
    main()
