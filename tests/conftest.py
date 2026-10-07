"""Keep test settings and profiles isolated from the user's workspace."""
from pathlib import Path
import shutil
import pytest

@pytest.fixture(autouse=True)
def isolated_ui_assets(request):
    if 'tmp_path' in request.fixturenames:
        root=Path(__file__).resolve().parents[1]
        destination=request.getfixturevalue('tmp_path')/'resources'
        shutil.copytree(root/'resources',destination)
