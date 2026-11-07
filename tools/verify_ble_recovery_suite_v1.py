"""Run 2.8.3 regression tests without touching connected boards or cloud accounts."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-font-registration', action='store_true',
                        help='Skip repeated Windows font registration in offscreen fixtures; verify packaged screenshots separately')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    if args.skip_font_registration:
        from PySide6 import QtGui
        QtGui.QFontDatabase.addApplicationFont = lambda *args: -1
    import pytest
    return pytest.main(['-c', str(root / 'pytest.ble-recovery.v1.ini'), '-q',
                        '--junitxml=' + str(root / 'verification/ble-recovery-tests.v1.xml')])


if __name__ == '__main__':
    raise SystemExit(main())
