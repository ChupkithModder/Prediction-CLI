"""Local read-only JSON view, optional explicit control-request file. No backend."""
import csv
import json
import re
import time
import uuid
from pathlib import Path

from .protocol import MAX_BYTES,decode,empty_snapshot,demo_snapshot,validate_event,validate_snapshot


class Frontend:
    def __init__(self,snapshot_path=None,events_path=None,requests_path=None,demo=False):
        if snapshot_path and events_path:raise ValueError('Choose --snapshot or --events, not both')
        if demo and (snapshot_path or events_path):raise ValueError('Demo cannot be mixed with external data')
        self.snapshot_path=Path(snapshot_path).expanduser() if snapshot_path else None
        self.events_path=Path(events_path).expanduser() if events_path else None
        self.requests_path=Path(requests_path).expanduser() if requests_path else None
        self.snapshot=demo_snapshot() if demo else empty_snapshot()
        self.error=''
        self._signature=None
        self.selected_model=self.snapshot['model']

    def refresh(self):
        path=self.snapshot_path or self.events_path
        if not path:return self.snapshot
        try:
            stat=path.stat()
            signature=(stat.st_mtime_ns,stat.st_size)
            if signature==self._signature:return self.snapshot
            if stat.st_size>MAX_BYTES:raise ValueError('Input exceeds 1 MB; backend must rotate the local file')
            raw=path.read_bytes()
            if len(raw)>MAX_BYTES:raise ValueError('Input exceeds 1 MB')
            if self.snapshot_path:
                updated=validate_snapshot(decode(raw))
            else:
                records=[]
                for line in raw.splitlines():
                    if line.strip():records.append(validate_event(decode(line),stream=True))
                if len(records)>200:raise ValueError('Event file exceeds 200 rows; backend must rotate it')
                if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate event ids')
                updated=empty_snapshot()
                updated['events']=records
                if records:
                    latest=max(records,key=lambda r:r['at'])
                    updated.update(as_of=latest['at'],model=latest['model'],models=list(dict.fromkeys(r['model'] for r in records)))
                    statuses=[r for r in records if r.get('status')]
                    if statuses:updated['status']=max(statuses,key=lambda r:r['at'])['status']
                    updated['metrics']['skipped']=sum(r['type']=='skip' for r in records)
            self.snapshot=updated
            if self.selected_model=='unconfigured':self.selected_model=updated['model']
            self.error=''
            self._signature=signature
        except (ValueError,OSError) as e:
            self.error=str(e)
        return self.snapshot

    def request(self,command,model=None):
        if command not in ('start','stop','model'):raise ValueError('Unknown control request')
        if not self.requests_path:raise ValueError('No backend control file configured. Use --requests PATH; this frontend never starts or stops a backend itself.')
        event={'schema':'prediction-cli-control-v1','request_id':uuid.uuid4().hex,'requested_at':int(time.time()),'command':command}
        if model is not None:
            if not isinstance(model,str) or not 1<=len(model)<=80 or any(ord(c)<32 for c in model):raise ValueError('Invalid model id')
            event['model']=model
        self.requests_path.parent.mkdir(parents=True,exist_ok=True)
        with self.requests_path.open('a',encoding='utf-8') as file:file.write(json.dumps(event,separators=(',',':'))+'\n')
        return event

    def export(self,path,format='csv'):
        path=Path(path).expanduser()
        path.parent.mkdir(parents=True,exist_ok=True)
        self.refresh()
        with path.open('x',encoding='utf-8-sig' if format=='csv' else 'utf-8',newline='') as file:
            if format=='json':json.dump(self.snapshot,file,indent=2,allow_nan=False)
            else:
                columns=('id','type','at','model','decision','p_up','outcome','summary','status')
                writer=csv.writer(file,quoting=csv.QUOTE_ALL);writer.writerow(columns)
                for row in self.snapshot['events']:
                    values=[]
                    for k in columns:
                        v=row.get(k,'')
                        if isinstance(v,str) and re.match(r'^[\s\x00-\x1f]*[=+@-]',v):v="'"+v
                        values.append(v)
                    writer.writerow(values)
        return path
