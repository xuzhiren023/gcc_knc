"""Write STATUS.md, the project manager's view of the board, and send a desktop notification.

tools/pm.py calls this on every ticket change, so nobody has to ask for an update. Neither
step is allowed to stop the work if it fails.
"""
import datetime
import json
import os
import re
import shutil
import subprocess

import storage

ENTRY = re.compile(r"^- (\d{4}-\d\d-\d\d)(?: (\d\d:\d\d))? (\w+) ([\w-]+): (.*)$")
STATES = {
    "ready": "Not started",
    "doing": "In progress",
    "red-review": "Tests waiting for review",
    "review": "Waiting for review",
    "changes": "Changes requested",
    "blocked": "Question for the tech lead",
    "owner": "**Waiting for you**",
    "done": "Done",
}
UPDATES = {
    "doing": "{id} is in progress: {title}.",
    "red-review": "{id}: failing tests are ready for the tech lead.",
    "review": "{id} is finished and waiting for review: {title}.",
    "changes": "{id}: the tech lead asked for changes.",
    "blocked": "{id}: GPT asked the tech lead a question.",
    "owner": "{id} needs your decision. Run: python tools/pm.py inbox",
    "done": "{id} is approved and merged: {title}.",
}
NOTIFY_STATES = ("review", "blocked", "owner", "done", "changes", "red-review")


def update_line(ticket):
    template = UPDATES.get(ticket.state, "{id} is now " + ticket.state + ".")
    return template.format(id=ticket.id, title=ticket.fields.get("title", ""))


def entries(ticket):
    found = []
    for line in ticket.body.splitlines():
        match = ENTRY.match(line)
        if match:
            date, clock, role, verb, text = match.groups()
            found.append((date, clock or "", ticket.id, role, verb, text))
    return found


def bar(done, total, width=20):
    filled = int(width * done / total) if total else 0
    return "`[%s%s]` %d of %d" % ("#" * filled, "-" * (width - filled), done, total)


def next_step(board, action, tickets):
    waiting = [t.id for t in tickets if t.state == "owner"]
    if waiting:
        return "**Waiting for you:** %s. Run `python tools/pm.py inbox`." % ", ".join(waiting)
    if action is None:
        if tickets and all(t.state == "done" for t in tickets):
            return "All current tickets are done. The tech lead plans the next sprint."
        return "Nothing can move right now."
    role, ticket = action
    if role == "lead":
        return ("**Next: the tech lead, on %s.** Ask a Claude session in this folder: "
                "\"Act as tech lead. Handle what the board needs.\"" % ticket.id)
    return "**Next: GPT-6.1, on %s (%s).** Start a new session and paste the prompt from `KICKOFF.md`." % (
        ticket.id, ticket.fields.get("title", ""))


def milestone_rows(board, tickets):
    path = os.path.join(board.root, "work", "milestones.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf8") as f:
        milestones = json.load(f)
    rows = []
    for item in milestones:
        mine = [t for t in tickets if t.fields.get("sprint") in item["sprints"]]
        done = sum(t.state == "done" for t in mine)
        if item.get("done"):
            state = "Done"
        elif any(t.state != "ready" for t in mine):
            state = "In progress"
        else:
            state = "Not started"
        count = "%d of %d tickets" % (done, len(mine)) if mine else "Not planned in detail yet"
        rows.append("| %s | %s | %s | %s |" % (item["id"], item["name"], state, count))
    return rows


def usage_lines(board):
    path = os.path.join(board.state_dir(), "ledger.jsonl")
    totals = {}
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            for line in f:
                entry = json.loads(line)
                item = totals.setdefault(entry["role"], [0, 0])
                item[0] += 1
                item[1] += entry.get("input_tokens", 0)
    if not totals:
        return ["No dispatcher sessions yet. Sessions you start by hand show their use in the app, not here."]
    rows = ["- %s: %d sessions, %.1fM input tokens" % (role, n, tokens / 1e6) for role, (n, tokens) in sorted(totals.items())]
    return rows + ["- Counts dispatcher sessions only, not sessions you start by hand."]


def render(board, action):
    tickets = board.tickets()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    done = sum(t.state == "done" for t in tickets)
    out = ["# GCC-KNC status", "", "Updated automatically at every ticket change. Last update: %s." % now, "",
           next_step(board, action, tickets), "", "Current tickets: " + bar(done, len(tickets)), ""]
    rows = milestone_rows(board, tickets)
    if rows:
        out += ["## Milestones", "", "| | Milestone | State | Progress |", "|---|---|---|---|"] + rows + [""]
    out += ["## Tickets", "", "| Ticket | What | State | Latest |", "|---|---|---|---|"]
    all_entries = []
    for ticket in tickets:
        mine = entries(ticket)
        all_entries += mine
        latest = mine[-1][5] if mine else ""
        latest = latest if len(latest) <= 110 else latest[:107] + "..."
        out.append("| %s | %s | %s | %s |" % (ticket.id, ticket.fields.get("title", ""), STATES.get(ticket.state, ticket.state),
                                              latest.replace("|", "/")))
    out += ["", "## Recent activity", ""]
    recent = sorted(all_entries, key=lambda e: e[:2])[-8:]
    for date, clock, ident, role, verb, text in reversed(recent):
        text = text if len(text) <= 150 else text[:147] + "..."
        out.append("- %s %s **%s** %s %s: %s" % (date, clock, ident, role, verb, text))
    if not recent:
        out.append("Nothing yet.")
    out += ["", "## Cost", ""] + usage_lines(board)
    level, message = storage.check(board.root, board.policy)
    free = shutil.disk_usage(board.root).free / storage.GIB
    out += ["", "## Disk", "", "%s %.0f GiB free on the drive." % (message, free), ""]
    return "\n".join(out)


def status_path(board):
    return os.path.join(board.root, "STATUS.md")


def write(board, action):
    with open(status_path(board), "w", encoding="utf8", newline="\n") as f:
        f.write(render(board, action))
    return status_path(board)


TOAST = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $x.GetElementsByTagName('text')
$t.Item(0).AppendChild($x.CreateTextNode('{title}')) | Out-Null
$t.Item(1).AppendChild($x.CreateTextNode('{body}')) | Out-Null
$n = [Windows.UI.Notifications.ToastNotification]::new($x)
$id = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show($n)
"""


def notify(title, body, wait=False):
    """Show a Windows notification. Best effort: it must never delay or break the work."""
    if os.environ.get("PM_NO_NOTIFY") or os.name != "nt":
        return None
    script = TOAST.format(title=title.replace("'", "''"), body=body.replace("'", "''"))
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
    if wait:
        return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None
