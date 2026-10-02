"""Quiet OpenCode-inspired slash-command UI; stdlib POSIX/Windows input."""
import os
import re
import shutil
import sys
import time


RESET = "\033[0m"
CYAN = "\033[38;5;81m"
GREEN = "\033[38;5;114m"
PURPLE = "\033[38;5;183m"
DIM = "\033[38;5;245m"
AMBER = "\033[38;5;221m"
WHITE = "\033[38;5;255m"
LOGO = (
    " ___  ___  ___  ___  _  ___ _____ _  ___  _  _ ",
    "| _ \\| _ \\| __||   \\| || __|_   _| || _ \\| \\| |",
    "|  _/|   /| _| | |) | || (__ | | | || (_) | .` |",
    "|_|  |_|_\\|___||___/|_| \\___||_| |_| \\___/|_|\\_|",
)


def clean(value, width=10000):
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(value or "")).encode("ascii", "replace").decode()[:width]


def percentage(value):
    return "--" if value is None else f"{value*100:.1f}%"


def utc(at):
    return time.strftime("%H:%M", time.gmtime(at)) if at is not None else "--:--"


def duration(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}"


class Terminal:
    def __enter__(self):
        self.original = None
        if os.name == "nt":
            import ctypes
            kernel = ctypes.windll.kernel32
            handle = kernel.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if not kernel.GetConsoleMode(handle, ctypes.byref(mode)) or not kernel.SetConsoleMode(handle, mode.value | 4):
                raise ValueError("Use Windows Terminal or a terminal with ANSI color support")
        else:
            import termios
            import tty
            self.original = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
        sys.stdout.write("\033[?1049h\033[?25l")
        sys.stdout.flush()
        return self

    def __exit__(self, *_):
        if self.original:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.original)
        sys.stdout.write(RESET+"\033[?25h\033[?1049l")
        sys.stdout.flush()

    def key(self, wait=.25):
        if os.name == "nt":
            import msvcrt
            until = time.monotonic()+wait
            while time.monotonic() < until:
                if msvcrt.kbhit():
                    key = msvcrt.getwch()
                    if key in ("\x00", "\xe0"):
                        return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
                    return key
                time.sleep(.03)
            return ""
        import select
        if select.select([sys.stdin], [], [], wait)[0]:
            key = os.read(sys.stdin.fileno(), 1024).decode("utf-8", errors="ignore")
            return {"\033[A": "up", "\033[B": "down"}.get(key, key)
        return ""


def render(snapshot,width=100,height=32,tab='home',selected=None,toast='',error='',offset=0,input_text=''):
    width,height=max(40,width),max(12,height);inner=width-6
    metrics=snapshot['metrics'];events=snapshot['events'];model=snapshot['model']
    score=metrics['forecast_score']
    badge=(f'score {score:.3f}' if score is not None else 'score --')+f"  accuracy {percentage(metrics['accuracy'])}  skips {metrics['skipped']}"
    lines=[]
    def line(text='',color=WHITE):lines.append('  '+color+clean(text,inner).ljust(inner)+RESET+'  ')
    def center(text,color=DIM):line(clean(text).center(inner),color)
    line('Prediction CLI'+' '*max(2,inner-14-len(badge))+badge,DIM)
    context='synthetic interface demo / no backend or model ran' if snapshot['mode']=='synthetic' else 'external forecast view / '+snapshot['status']
    if snapshot['mode']=='external' and snapshot['as_of']:
        age=int(time.time())-snapshot['as_of']
        if age>90:context+=' / stale snapshot'
        elif age< -20:context+=' / future timestamp'
    line(context,AMBER if snapshot['mode']=='synthetic' or error else DIM)
    if width<70 or height<24:
        line('Expand terminal to 70 columns x 24 rows',AMBER);line('/start /stop /model /stats /logs /export /help');line(error or toast,AMBER);line('> '+input_text)
        return '\033[H\033[2J'+'\n'.join(lines[:height-1])
    if tab=='stats':
        line();line('Backend-reported forecast details')
        line('Model: '+model,DIM)
        line(f"Forecast score {score if score is not None else '--'} / accuracy {percentage(metrics['accuracy'])} / skipped {metrics['skipped']}",DIM)
        line('No inference, scoring, scheduling, accounts or orders run in this frontend',DIM)
        line('The external backend owns metric definitions and execution',DIM)
    elif tab=='logs':
        line();line('External event log / UTC')
        for r in list(reversed(events))[offset:offset+max(1,height-11)]:line(f"{utc(r['at'])}  {r['type']}  {r['model']}  {r['summary']}",DIM)
        if not events:line('No external events yet',DIM)
    elif tab=='help':
        line()
        for item in ('/start          emit a start request, if --requests is configured','/stop           emit a stop request, if --requests is configured','/model [id]     show/select a backend-declared model','/stats          backend-reported metrics','/logs           external events; arrows scroll','/export         save visible events as CSV locally','/home           return to summaries','/quit           close this frontend'):
            line(item,DIM)
        line();line('Requests are local JSON messages. The backend must acknowledge them',DIM)
        line('No backend, model execution, scheduling or financial tracker is bundled',DIM)
    else:
        for _ in range(max(1,(height-26)//2+1)):line()
        for logo in LOGO:center(logo,WHITE)
        center('C L I  /  v1.0.0',DIM);line()
        center('/start  request       /model  choose       /help  commands',DIM);line()
        if events:
            for r in events[-max(1,min(3,height-24)):]:line(f"{utc(r['at'])}  {r['summary']}",DIM)
        else:line('Connect a local JSON feed. The details stay behind /stats and /logs',DIM)
    while len(lines)<height-8:line()
    line(error or toast,AMBER)
    line('+'+'-'*(inner-2)+'+',DIM)
    line('| > '+clean(input_text,inner-6).ljust(inner-6)+' |')
    line('+'+'-'*(inner-2)+'+',DIM)
    line((selected or model)+' / JSON view / backend-declared identity',DIM)
    line('Enter send   /help commands   Ctrl+C leave',DIM)
    return '\033[H\033[2J'+'\n'.join(lines[:height-1])


def run_tui(frontend):
    if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Interactive UI needs a terminal. Use status --json in scripts.')
    tab,toast,offset,text='home','',0,''
    with Terminal() as terminal:
        while True:
            snapshot=frontend.refresh();size=shutil.get_terminal_size((100,32))
            sys.stdout.write(render(snapshot,size.columns,size.lines,tab,frontend.selected_model,toast,frontend.error,offset,text));sys.stdout.flush()
            key=terminal.key(.5)
            if not key:continue
            if key=='\x03':break
            if key in ('up','down'):
                offset=max(0,min(max(0,len(snapshot['events'])-1),offset+(1 if key=='down' else -1)));continue
            for char in key:
                if char in ('\x7f','\x08'):text=text[:-1]
                elif char=='\033':text=''
                elif char in ('\r','\n'):
                    parts=text.strip().split();text=''
                    if not parts:continue
                    command,args=parts[0].lower(),parts[1:]
                    try:
                        if command in ('/quit','/exit'):return 0
                        if command in ('/home','/help','/stats','/logs'):tab=command[1:];toast='';offset=0
                        elif command in ('/start','/stop'):
                            frontend.request(command[1:],frontend.selected_model if command=='/start' and frontend.selected_model in snapshot['models'] else None)
                            toast=command[1:].capitalize()+' requested. Waiting for external backend acknowledgment'
                        elif command=='/model':
                            if args:
                                if args[0] not in snapshot['models']:raise ValueError('Model is not declared by the configured backend')
                                frontend.selected_model=args[0]
                                if frontend.requests_path:frontend.request('model',args[0])
                                toast='Selected '+args[0]+(' / backend change requested' if frontend.requests_path else ' / view selection only')
                            else:toast='Backend-declared models: '+(', '.join(snapshot['models']) or 'none configured')
                        elif command=='/export':
                            path=time.strftime('prediction-log-%Y%m%d-%H%M%S.csv',time.gmtime());frontend.export(path);toast='Saved locally: '+path
                        else:toast='Try /start, /stop, /model, /stats, /logs, /export or /help'
                    except (ValueError,OSError) as e:toast=clean(e,max(50,size.columns-6))
                elif char.isprintable() and len(text)<300:text+=char
    return 0
