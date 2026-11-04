"""Create a NEW full desktop revision for battery Tag BLE calibration."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
def derive(source,target,changes):
    value=(ROOT/source).read_text(encoding='utf8')
    for old,new in changes:value=value.replace(old,new)
    with (ROOT/target).open('x',encoding='utf8',newline='\n') as output:output.write(value)
if __name__=='__main__':
    target=ROOT/'app/revisions/v10'
    if target.exists():raise FileExistsError(target)
    shutil.copytree(ROOT/'app/revisions/v9',target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for path in target.rglob('*.py'):
        path.write_text(path.read_text(encoding='utf8').replace('2.2.1','2.3.0').replace('th.v7.json','th.v8.json').replace('GUIDE.v5.','GUIDE.v6.'),encoding='utf8')
    version=[('2.2.1','2.3.0'),('2_2_1','2_3_0')]
    launcher=[('distribution.v5.json','distribution.v6.json'),('Launcher_v5.exe','Launcher_v6.exe'),('Bootstrap.v5.cs','Bootstrap.v6.cs')]
    for source,target,changes in [
        ('tools/package_desktop_v9.py','tools/package_desktop_v10.py',version+[('v9','v10')]),
        ('tools/build_github_distribution_v5.py','tools/build_github_distribution_v6.py',version+launcher+[('desktop-v9','desktop-v10')]),
        ('tools/verify_github_distribution_v5.py','tools/verify_github_distribution_v6.py',version+launcher+[('github-portable-v5-','github-portable-v6-')]),
        ('deployment/Bootstrap.v5.cs','deployment/Bootstrap.v6.cs',version+launcher),
        ('START_HERE_2_2_1.cmd','START_HERE_2_3_0.cmd',launcher),
        ('resources/i18n/th.v7.json','resources/i18n/th.v8.json',version),
        ('tools/verify_auto_survey_ui_v2.py','tools/verify_auto_survey_ui_v3.py',[('app/revisions/v9','app/revisions/v10'),("str(ROOT/'app/ble_prototype/v1')","str(ROOT/'app/battery_calibration/v1'),str(ROOT/'app/ble_prototype/v1')")]),
        ('tools/install_auto_survey_shortcut_v2.py','tools/install_auto_survey_shortcut_v3.py',version+launcher)]:derive(source,target,changes)
    for language in ('en','th'):derive('docs/INTEGRATED_STANDALONE_GUIDE.v5.'+language+'.md','docs/INTEGRATED_STANDALONE_GUIDE.v6.'+language+'.md',version)
    derive('pytest.auto-survey.v2.ini','pytest.battery-desktop.v1.ini',[('app/revisions/v9','app/revisions/v10 app/battery_calibration/v1')])
    print('Created full desktop v10 / 2.3.0 in new paths.')
