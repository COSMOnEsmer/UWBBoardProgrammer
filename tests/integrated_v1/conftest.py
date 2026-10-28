from pathlib import Path
import shutil
import pytest


@pytest.fixture(autouse=True)
def isolated_resources(request):
    if 'tmp_path' in request.fixturenames:
        destination=request.getfixturevalue('tmp_path')/'resources'
        if not destination.exists():
            shutil.copytree(Path(__file__).resolve().parents[2]/'resources',destination)
