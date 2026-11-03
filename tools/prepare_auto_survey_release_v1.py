"""Create append-only v2.2.0 release entry points from the previous build tools."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAIRS=[('tools/package_desktop_v7.py','tools/package_desktop_v8.py', [('v7','v8'),('2.1.2','2.2.0'),('2_1_2','2_2_0')]),
       ('tools/build_github_distribution_v3.py','tools/build_github_distribution_v4.py',[('desktop-v7','desktop-v8'),('v3','v4'),('2.1.2','2.2.0'),('2_1_2','2_2_0')]),
       ('tools/verify_github_distribution_v3.py','tools/verify_github_distribution_v4.py',[('v3','v4'),('2.1.2','2.2.0'),('2_1_2','2_2_0')]),
       ('deployment/Bootstrap.v3.cs','deployment/Bootstrap.v4.cs',[('v3','v4'),('2.1.2','2.2.0')]),
       ('START_HERE_2_1_2.cmd','START_HERE_2_2_0.cmd',[('v3','v4')])]
if __name__=='__main__':
    for source,target,changes in PAIRS:
        content=(ROOT/source).read_text(encoding='utf8')
        for before,after in changes:content=content.replace(before,after)
        content=content.replace('LGPLv4','LGPLv3')
        with (ROOT/target).open('x',encoding='utf8',newline='\n') as stream:stream.write(content)
        print(target)
