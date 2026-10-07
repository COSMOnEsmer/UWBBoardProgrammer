from pathlib import Path
import argparse,json,os,sys

def root_path():
    explicit=os.environ.get('UWB_BOARD_PROGRAMMER_ROOT')
    if explicit:return Path(explicit).resolve()
    origin=Path(sys.executable if getattr(sys,'frozen',False) else __file__).resolve()
    for folder in origin.parents:
        if (folder/'programmer-workspace.json').is_file():return folder
    raise RuntimeError('Application root missing. Keep the release inside UWB Board Programmer or use the supplied launcher.')

try:
    from uwb_board_programmer.gui import main,Window
except Exception:
    import traceback
    from datetime import datetime,timezone
    folder=root_path()/'data/startup-logs';folder.mkdir(parents=True,exist_ok=True)
    with (folder/('startup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.txt')).open('x',encoding='utf-8') as out:out.write(traceback.format_exc())
    raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--smoke-output');parser.add_argument('--screenshots');args=parser.parse_args();root=root_path()
    if args.smoke_output:
        from PySide6 import QtCore,QtWidgets as W
        app=W.QApplication(sys.argv);window=Window(root);window.show();app.processEvents()
        def finish():
            try:
                if args.screenshots:
                    folder=Path(args.screenshots);folder.mkdir(parents=True,exist_ok=True)
                    for index in range(window.tabs.count()):
                        window.tabs.setCurrentIndex(index);app.processEvents();path=folder/f'tab-{index+1}.png'
                        if path.exists():raise FileExistsError(path)
                        if not window.grab().save(str(path)):raise RuntimeError('Screenshot save failed')
                # Embedded SOFTWARE fixture only under explicit smoke-output flag.
                # No serial reader, RF generator or cloud publisher is constructed.
                import math,numpy as np
                from uwb_board_programmer.models import Profile,Observation,C_M_S,TICK_S
                from uwb_board_programmer.positioning import Solver
                profile=Profile();profile.bounds=[[0,0,0],[10,8,4]];truth=np.array([4.,3.,1.2]);observations={};times={}
                for anchor,xyz in zip(profile.anchors,[[0,0,2.7],[9,0,2.9],[0,7,1.5]]):
                    anchor.position=xyz;anchor.aoa_verified=True;d=truth-xyz
                    rx=(1<<62)+round(np.linalg.norm(d)/(C_M_S*TICK_S));times[anchor.id]=rx
                    az=math.degrees(math.atan2(d[1],d[0]));el=math.degrees(math.atan2(d[2],np.hypot(d[0],d[1])))
                    observations[anchor.id]=Observation(anchor.id,profile.tag_mac,'BLINK',0,rx,None,64,az,el,95,95,False,'software-fixture')
                fix=Solver(profile).solve(observations,times);error=float(np.linalg.norm(np.array([fix['x_m'],fix['y_m'],fix['z_m']])-truth))
                if error>.025:raise RuntimeError('Packaged numerical solver fixture failed')
                data={'software_fixture_error_m':error,'software_fixture_xyz':[fix['x_m'],fix['y_m'],fix['z_m']],'fixture_published':False,'packaged':bool(getattr(sys,'frozen',False)),'application_root':str(root),'tabs':window.tabs.count(),'firmware_bundles':window.firmware_combo.count(),'automatic_serial_open':window.controller is not None,'automatic_cloud_connect':window.cloud is not None,'version':'2.0.0'}
                with Path(args.smoke_output).open('x',encoding='utf-8') as out:json.dump(data,out,indent=2)
                window.close();app.quit()
            except Exception:
                import traceback
                with Path(args.smoke_output).with_suffix('.error.txt').open('x',encoding='utf-8') as out:out.write(traceback.format_exc())
                app.exit(1)
        QtCore.QTimer.singleShot(1000,finish);sys.exit(app.exec())
    sys.exit(main(root))
