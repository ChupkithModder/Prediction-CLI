"""Presentation-only Prediction CLI; local JSON in, optional requests out."""
import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__
from .frontend import Frontend
from .tui import clean,run_tui


def parser():
    p=argparse.ArgumentParser(prog='prediction-cli',description='Educational BTC/USD forecast frontend. No backend, model execution, scheduling, accounts or orders.')
    p.add_argument('--version',action='version',version='Prediction CLI '+__version__)
    p.add_argument('--snapshot',type=Path,help='Read and watch a typed local snapshot JSON file')
    p.add_argument('--events',type=Path,help='Read and watch a typed local JSONL event file')
    p.add_argument('--requests',type=Path,help='Explicit local JSONL output for control requests; no backend action is executed here')
    p.add_argument('--demo',action='store_true',help='Synthetic interface demo; no model or backend runs')
    sub=p.add_subparsers(dest='command');sub.add_parser('tui')
    for name in ('status','logs'):
        q=sub.add_parser(name);q.add_argument('--json',action='store_true')
    sub.add_parser('start',help='Append a start request only when --requests is explicitly configured')
    sub.add_parser('stop',help='Append a stop request only when --requests is explicitly configured')
    m=sub.add_parser('model');m.add_argument('name',nargs='?')
    e=sub.add_parser('export');e.add_argument('--output',type=Path);e.add_argument('--format',choices=('csv','json'),default='csv')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        frontend=Frontend(args.snapshot,args.events,args.requests,args.demo);snapshot=frontend.refresh();command=args.command or 'tui'
        if command=='tui':return run_tui(frontend)
        if frontend.error:raise ValueError(frontend.error)
        if command=='status':
            if args.json:print(json.dumps(snapshot,indent=2,allow_nan=False))
            else:
                print('Prediction CLI | presentation-only | '+snapshot['status'])
                print('Model: '+clean(snapshot['model'])+' (backend-declared)')
                if snapshot['mode']=='synthetic':print('SYNTHETIC INTERFACE DEMO: no backend or model ran')
                print('No backend execution or forecasting occurs in this client')
        elif command=='logs':
            if args.json:print(json.dumps(snapshot['events'],indent=2,allow_nan=False))
            else:
                for row in snapshot['events']:print(clean(row['summary']))
                if not snapshot['events']:print('No external events yet')
        elif command in ('start','stop'):
            frontend.request(command)
            print(command.capitalize()+' request written locally. External backend acknowledgment is required.')
        elif command=='model':
            if args.name:
                if args.name not in snapshot['models']:raise ValueError('Model is not declared by the backend')
                if not frontend.requests_path:raise ValueError('Use --requests to send a model selection request; no model execution is supported')
                frontend.request('model',args.name);print('Model selection requested: '+args.name)
            else:print('\n'.join(snapshot['models']) or 'No backend models configured')
        elif command=='export':
            path=args.output or Path(time.strftime('prediction-log-%Y%m%d-%H%M%S.'+args.format,time.gmtime()))
            print('Saved locally: '+str(frontend.export(path,args.format)))
        return 0
    except (ValueError,OSError) as e:
        print('Prediction CLI: '+clean(e),file=sys.stderr);return 2
    except KeyboardInterrupt:return 130
