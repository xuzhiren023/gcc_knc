#!/usr/bin/env python3
"""Read-only local card/twin dashboard; Python 3.8, standard library only."""
import argparse
import datetime as dt
import importlib.machinery
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

import pm

UTC = dt.timezone.utc
# Use the runner's queue liveness predicate, including its age and timingValid rules.
_runner = importlib.machinery.SourceFileLoader('dashboard_card_run', str(Path(__file__).with_name('card_run'))).load_module()


def timestamp(value):
    try:
        value = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value if value.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def ledger_status(text, now):
    active, finished, starts = {}, [], {}
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict) or not row.get('jobId'):
            continue
        key, event = row['jobId'], row.get('event', '')
        if event == 'start':
            starts[key] = row
        if event in ('finish', 'end'):
            merged = dict(starts.get(key, {}), **row)
            start, end = timestamp(merged.get('startTime')), timestamp(merged.get('endTime'))
            if start and end and end >= start:
                finished.append((merged, (end - start).total_seconds(), end))
        if event in ('start', 'queued'):
            active[key] = dict(row)
        elif event in ('finish', 'end', 'superseded') or 'cancel' in event:
            active.pop(key, None)
    running = [r for r in active.values() if r['event'] == 'start']
    for row in running:
        end = timestamp(row.get('expectedEnd'))
        row['remaining_seconds'] = (end - now).total_seconds() if end else None
    queue = sorted((r for r in active.values() if r['event'] == 'queued' and _runner.live_queue(r, now)),
                   key=lambda r: timestamp(r.get('firstQueuedTime')) or timestamp(r.get('queuedTime')))
    ends = [timestamp(r.get('expectedEnd')) for r in running]
    cursor = max(now, max(ends)) if ends and all(ends) else (now if not ends else None)
    jobs, turns = [], []
    for row in queue:
        if str(row['jobId']).startswith('claude-turn-') and row.get('cores') == []:
            turns.append(row)
            continue
        before = timestamp(row.get('firstQueuedTime')) or timestamp(row.get('queuedTime'))
        earlier = [(r, seconds) for r, seconds, end in finished if end <= before]
        durations = [seconds for r, seconds in earlier if row.get('purpose') and r.get('purpose') == row['purpose']]
        basis = 'purpose' if durations else None
        if not durations and row.get('project') and row.get('agent'):
            durations = [seconds for r, seconds in earlier
                         if (r.get('project'), r.get('agent')) == (row['project'], row['agent'])]
            basis = 'project and agent' if durations else None
        duration = statistics.median(durations) if durations else None
        row.update(duration_seconds=duration, basis=basis,
                   estimated_start=cursor.isoformat() if cursor else None)
        cursor = cursor + dt.timedelta(seconds=duration) if cursor and duration is not None else None
        jobs.append(row)
    return dict(running=running, queue=jobs, turns=turns, order=[r['jobId'] for r in queue])


def parse_micsmc(text):
    devices, device = {}, None
    for line in text.splitlines():
        match = re.match(r'\s*(mic\d+)\s*\(([^)]+)\):', line)
        if match:
            device = devices.setdefault(match[1], dict(temperatures={}, cores={}, utilization=None))
        elif device is not None:
            temp = re.match(r'\s*([^:]+):\s*\.*\s*(-?\d+(?:\.\d+)?)\s*C\b', line)
            values = re.findall(r'(User|System|Idle):\s*([\d.]+)%', line, re.I)
            if temp:
                device['temperatures'][temp[1].strip()] = float(temp[2])
            if len(values) == 3:
                utilization = {k.lower(): float(v) for k, v in values}
                core = re.search(r'Core\s*#(\d+)', line)
                if core:
                    device['cores'][core[1]] = utilization
                elif 'Device Utilization:' in line:
                    device['utilization'] = utilization
    if not devices or not any(d['temperatures'] or d['utilization'] or d['cores'] for d in devices.values()):
        raise ValueError('MicSmc output unavailable: ' + text.strip()[:200])
    return devices


def parse_host_cpu(text):
    values = json.loads(text)
    values = values if isinstance(values, list) else [values]
    if not values or any(not isinstance(v, (float, int)) or not math.isfinite(v) or not 0 <= v <= 100 for v in values):
        raise ValueError('Host CPU utilization unavailable')
    return statistics.mean(values)


def update_history(history, processes, now):
    durations = history.get('durations', {})
    active = {p['key']: dict(p) for p in processes}
    for key, old in history.get('active', {}).items():
        if key not in active and old.get('start_epoch') is not None:
            # Completion is observed at this refresh: includes up to one refresh interval.
            seconds = now - old['start_epoch']
            if seconds >= 0:
                durations.setdefault(old['subcommand'], []).append(seconds)
                durations[old['subcommand']] = durations[old['subcommand']][-100:]
    result = []
    for process in processes:
        row = dict(process)
        elapsed = now - row['start_epoch'] if row.get('start_epoch') is not None else None
        samples = durations.get(row['subcommand'], [])
        row.update(elapsed_seconds=elapsed, remaining_seconds=(statistics.median(samples) - elapsed)
                   if samples and elapsed is not None else None,
                   basis='observed completion median (refresh resolution)' if samples else None)
        result.append(row)
    return dict(active=active, durations=durations), result


def command(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
                            encoding='utf-8', errors='replace')
    if result.returncode:
        raise OSError((result.stderr or result.stdout or 'exit %s' % result.returncode).strip()[:400])
    return result.stdout.lstrip('\ufeff')


def powershell(script):
    return command(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                    "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; " + script])


def twin_processes():
    raw = powershell("@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match 'knc_twin\\.py' } | ForEach-Object { @{pid=$_.ProcessId; command=$_.CommandLine; start=$_.CreationDate.ToUniversalTime().ToString('o')} }) | ConvertTo-Json -Compress")
    rows = json.loads(raw or '[]')
    rows = rows if isinstance(rows, list) else [rows]
    result = []
    for row in rows:
        match = re.search(r'knc_twin\.py["\x27]?\s+([^\s"\x27]+)', row['command'])
        start = timestamp(row.get('start'))
        result.append(dict(key='%s:%s' % (row['pid'], row['start']), pid=row['pid'],
                           subcommand=match[1] if match else 'unknown', command=row['command'],
                           start_time=row['start'],
                           start_epoch=start.timestamp() if start else None))
    return result


def twin_tickets(board, now):
    rows = []
    logs = Path(board.root) / '.work/_state/logs'
    timeout = board.policy['session_timeout_minutes'] * 60
    for ticket in board.tickets():
        if ticket.state != 'doing' or not pm.lane_of(ticket).startswith('twin-'):
            continue
        sessions = []
        for path in logs.glob(ticket.id + '-*.jsonl'):
            match = re.fullmatch(re.escape(ticket.id) + r'-(?:engineer|lead)-(\d{4}-\d{2}-\d{2}T\d{6})\.jsonl', path.name)
            if match:
                try:
                    # Dispatcher filenames use host local time, including its DST rules.
                    start = dt.datetime.strptime(match[1], '%Y-%m-%dT%H%M%S').astimezone(UTC)
                    sessions.append((start, path))
                except ValueError:
                    continue
        start = None
        if sessions:
            candidate, path = max(sessions, key=lambda session: session[0])
            if now.timestamp() - path.stat().st_mtime <= timeout:
                start = candidate
        rows.append(dict(id=ticket.id, title=ticket.fields.get('title'),
                         session_start=start.isoformat() if start else None,
                         session_status='live' if start else 'no live session',
                         remaining_seconds=timeout - (now - start).total_seconds()
                         if start else None, basis='session timeout upper bound'))
    return rows


def collect(board):
    now = dt.datetime.now(UTC)
    def panel(fn):
        try:
            return dict(read_at=dt.datetime.now(UTC).isoformat(), status='ok', data=fn())
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            return dict(read_at=dt.datetime.now(UTC).isoformat(), status='unavailable', error=str(error))
    root = Path(board.root)
    def card():
        config = root / 'config/card.local.json'
        settings = json.loads(config.read_text(encoding='utf-8')) if config.exists() else {}
        path = Path(settings.get('ledger', 'C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl'))
        return ledger_status(path.read_text(encoding='utf-8-sig'), now)
    def twins():
        processes = twin_processes()  # A failed process query must not close history entries.
        path = root / '.work/_state/dashboard-twin-history.json'
        try:
            history = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            history = {}
        history, rows = update_history(history, processes, time.time())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(history), encoding='utf-8')
        return rows
    return dict(collected_at=now.isoformat(), card=panel(card),
                sensors=panel(lambda: parse_micsmc(command(['C:/Program Files/Intel/MPSS/bin/MicSmc.exe', '-t', '-c']))),
                host=panel(lambda: parse_host_cpu(powershell('@(Get-CimInstance Win32_Processor | ForEach-Object { $_.LoadPercentage }) | ConvertTo-Json -Compress'))),
                twin_processes=panel(twins), twin_tickets=panel(lambda: twin_tickets(board, now)))


HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KNC dashboard</title><style>
:root{color-scheme:light dark;font:16px system-ui}body{max-width:1200px;margin:auto;padding:18px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:16px}
section{border:1px solid #8888;border-radius:10px;padding:16px;min-width:0}h2{margin-top:0}
article{border-top:1px solid #8885;padding:10px 0;overflow-wrap:anywhere}small{opacity:.75}
button{padding:10px;font:inherit}pre{white-space:pre-wrap;overflow-wrap:anywhere}.strip{display:flex;gap:2px;flex-wrap:wrap}
.core{min-width:22px;padding:3px;text-align:center;color:black;font-size:12px;border:1px solid #888}
</style><h1>KNC card &amp; twin</h1><button id="refresh">Refresh now</button> <span id="status">Loading…</span>
<p>Refreshes every 5 minutes. Estimates are predictions. Negative remaining time means overdue.</p>
<main><section><h2>Card job</h2><div id="card"></div></section><section><h2>Card queue</h2><div id="queue"></div></section>
<section><h2>Twin work</h2><div id="twins"></div></section><section><h2>Card sensors</h2><div id="sensors"></div></section>
<section><h2>Host CPU</h2><div id="host"></div></section></main><script>
const el=id=>document.getElementById(id), esc=x=>String(x??'unknown').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const duration=x=>x==null?'unknown':(x<0?'overdue by ':'')+Math.round(Math.abs(x)/60)+' min';
const stamp=p=>'<small>Read '+esc(p.read_at)+'</small>', unavailable=p=>stamp(p)+'<p>unavailable: '+esc(p.error)+'</p>';
const rows=(a,fn)=>a.length?a.map(x=>'<article>'+fn(x)+'</article>').join(''):'<p>None observed</p>';
const job=r=>'<b>'+esc(r.jobId)+'</b><br>'+esc(r.project)+' / '+esc(r.agent)+'<br>'+esc(r.purpose);
async function refresh(force=false){el('refresh').disabled=true;try{
 const response=await fetch('/api/status'+(force?'?force=1':''));if(!response.ok)throw Error('HTTP '+response.status);const s=await response.json();
 el('status').textContent='Collected '+s.collected_at;
 const c=s.card;el('card').innerHTML=c.status==='ok'?stamp(c)+rows(c.data.running,r=>job(r)+'<br>Remaining: '+duration(r.remaining_seconds)):unavailable(c);
 el('queue').innerHTML=c.status==='ok'?stamp(c)+rows(c.data.turns,r=>'Turn marker: '+job(r))+'<p>Ledger order: '+esc(c.data.order.join(' → '))+'</p>'+rows(c.data.queue,r=>job(r)+'<br>Estimated start: '+esc(r.estimated_start)+'<br>Duration: '+duration(r.duration_seconds)+' ('+esc(r.basis)+')'):unavailable(c);
 const p=s.twin_processes,t=s.twin_tickets;el('twins').innerHTML='<h3>Host processes</h3>'+(p.status==='ok'?stamp(p)+rows(p.data,r=>'<b>'+esc(r.subcommand)+'</b> / PID '+esc(r.pid)+'<br>Command: '+esc(r.command)+'<br>Start: '+esc(r.start_time)+'<br>Elapsed: '+duration(r.elapsed_seconds)+'<br>Remaining: '+duration(r.remaining_seconds)+'<br>'+esc(r.basis)):unavailable(p))+'<h3>Board tickets</h3>'+(t.status==='ok'?stamp(t)+rows(t.data,r=>esc(r.id)+' '+esc(r.title)+'<br>Session: '+esc(r.session_status)+'<br>Session start: '+esc(r.session_start)+'<br>Remaining upper bound: '+duration(r.remaining_seconds)):unavailable(t));
 const m=s.sensors;el('sensors').innerHTML=m.status==='ok'?stamp(m)+Object.entries(m.data).map(([name,d])=>'<article><b>'+esc(name)+'</b><pre>'+esc(Object.keys(d.temperatures).length?JSON.stringify(d.temperatures,null,2):'unknown')+' °C</pre><p>Device user/system/idle: '+(d.utilization?['user','system','idle'].map(k=>esc(d.utilization[k])+'%').join(' / '):'unknown')+'</p><div class="strip">'+Array.from({length:61},(_,index)=>{const i=index+('0' in d.cores?0:1),v=d.cores[i],busy=v?100-v.idle:null;return '<span class="core" title="'+esc('Core '+i+': '+(v?JSON.stringify(v):'unknown'))+'" style="background:'+(busy==null?'#aaa':'hsl('+(120-busy*1.2)+',75%,65%)')+'">'+i+'</span>'}).join('')+'</div><small>Core busy = user + system; gray = unknown. Hover for percentages.</small></article>').join(''):unavailable(m);
 const h=s.host;el('host').innerHTML=h.status==='ok'?stamp(h)+'<p>'+esc(h.data)+'%</p>':unavailable(h);
 }catch(e){el('status').textContent='unavailable: '+e.message}finally{el('refresh').disabled=false}}
el('refresh').onclick=()=>refresh(true);refresh();setInterval(refresh,300000);
</script></html>'''


class Cache:
    def __init__(self, board):
        self.board, self.lock, self.value, self.last = board, threading.Lock(), None, None

    def get(self, force=False):
        with self.lock:
            age = time.monotonic() - self.last if self.last is not None else float('inf')
            if self.value is None or age >= 300 or (force and age >= 30):
                self.value = collect(self.board)
                self.last = time.monotonic()
            return self.value


def handler(cache):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == '/':
                data, mime = HTML.encode('utf-8'), 'text/html; charset=utf-8'
            elif url.path == '/api/status':
                data, mime = json.dumps(cache.get(parse_qs(url.query).get('force') == ['1'])).encode('utf-8'), 'application/json'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('snapshot')
    sub.add_parser('serve').add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    board = pm.Board()
    if args.action == 'snapshot':
        print(json.dumps(collect(board), indent=2))
    else:
        with ThreadingHTTPServer(('127.0.0.1', args.port), handler(Cache(board))) as server:
            print('KNC dashboard: http://127.0.0.1:%d/' % args.port, flush=True)
            server.serve_forever()


if __name__ == '__main__':
    main()
