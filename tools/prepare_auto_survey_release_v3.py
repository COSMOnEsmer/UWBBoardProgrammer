"""Create 2.2.1 in new revision paths; preserve every published 2.2.0 file."""
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]

def new_text(source,target,replacements):
    value=(ROOT/source).read_text(encoding='utf8')
    for before,after in replacements:value=value.replace(before,after)
    with (ROOT/target).open('x',encoding='utf8',newline='\n') as out:out.write(value)

if __name__=='__main__':
    source=ROOT/'app/revisions/v8';target=ROOT/'app/revisions/v9'
    if target.exists():raise FileExistsError(target)
    shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for path in target.rglob('*.py'):
        value=path.read_text(encoding='utf8').replace('2.2.0','2.2.1').replace('th.v6.json','th.v7.json').replace('GUIDE.v4.','GUIDE.v5.')
        path.write_text(value,encoding='utf8')
    version=[('2.2.0','2.2.1'),('2_2_0','2_2_1')]
    launcher=[('distribution.v4.json','distribution.v5.json'),('Launcher_v4.exe','Launcher_v5.exe'),('Bootstrap.v4.cs','Bootstrap.v5.cs')]
    pairs=[('tools/package_desktop_v8.py','tools/package_desktop_v9.py',version+[('v8','v9')]),
           ('tools/build_github_distribution_v4.py','tools/build_github_distribution_v5.py',version+launcher+[('desktop-v8','desktop-v9')]),
           ('tools/verify_github_distribution_v4.py','tools/verify_github_distribution_v5.py',version+launcher+[('github-portable-v4-','github-portable-v5-')]),
           ('deployment/Bootstrap.v4.cs','deployment/Bootstrap.v5.cs',version+launcher),
           ('START_HERE_2_2_0.cmd','START_HERE_2_2_1.cmd',launcher),
           ('resources/i18n/th.v6.json','resources/i18n/th.v7.json',version),
           ('tools/verify_auto_survey_ui_v1.py','tools/verify_auto_survey_ui_v2.py',[('app/revisions/v8','app/revisions/v9')]),
           ('tools/install_auto_survey_shortcut_v1.py','tools/install_auto_survey_shortcut_v2.py',version+launcher)]
    for source,target,changes in pairs:new_text(source,target,changes)
    for language in ('en','th'):
        new_text('docs/INTEGRATED_STANDALONE_GUIDE.v4.'+language+'.md','docs/INTEGRATED_STANDALONE_GUIDE.v5.'+language+'.md',version)
    new_text('pytest.auto-survey.v1.ini','pytest.auto-survey.v2.ini',[('app/revisions/v8','app/revisions/v9'),('tests/auto_survey_v1','tests/auto_survey_v2')])
    shutil.copytree(ROOT/'tests/auto_survey_v1',ROOT/'tests/auto_survey_v2',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    print('Created fresh app v9, 2.2.1 build/launch files, guides and tests.')
