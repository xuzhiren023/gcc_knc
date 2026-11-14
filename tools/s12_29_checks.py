"""S12-29 assembly check for broadcast memory alignment in small C probes.

Check declared constant alignment and stack-address residues, rather than
forbidding all constant-pool or stack broadcasts. Unknown address forms fail
closed. This is a straight-line frame tracker, not a general CFG analyzer.
"""
import math
import re


def broadcast_alignment(assembly):
    lines = assembly.splitlines()
    constants = {}
    alignment = 1
    for line in lines:
        text = line.strip()
        align = re.fullmatch(r'\.(align|balign|p2align)\s+(\d+)', text)
        label = re.fullmatch(r'(\.LC[\w.]+):', text)
        data = re.fullmatch(r'\.(byte|short|word|long|quad)\s+(.+)', text)
        if align:
            alignment = int(align[2])
            if align[1] == 'p2align':
                alignment = 1 << alignment
        elif label:
            constants[label[1]] = alignment
        elif data:
            size = {'byte': 1, 'short': 2, 'word': 2, 'long': 4, 'quad': 8}[data[1]]
            alignment = math.gcd(alignment, size * len(data[2].split(',')))
        elif text and not text.startswith(('.type', '.size', '.globl', '.local', '#')):
            alignment = 1

    functions = set(re.findall(r'\.type\s+(\S+),\s*@function', assembly))
    residues = {'rsp': 0, 'rbp': None}  # Entry stack address is a multiple of 8.
    failures = []
    function = '<unknown>'
    for number, line in enumerate(lines, 1):
        text = line.strip()
        if text.endswith(':') and text[:-1] in functions:
            function = text[:-1]
            residues = {'rsp': 0, 'rbp': None}
        adjust = re.fullmatch(r'(addq|subq|andq)\s+\$(-?\d+),\s*%rsp', text)
        copy = re.fullmatch(r'movq\s+%(rsp|rbp),\s*%(rsp|rbp)', text)
        if adjust:
            value = int(adjust[2])
            if adjust[1] == 'andq':
                residues['rsp'] = 0 if value % 8 == 0 else None
            elif residues['rsp'] is not None:
                residues['rsp'] = (residues['rsp'] + (value if adjust[1] == 'addq' else -value)) % 8
        elif copy:
            residues[copy[2]] = residues[copy[1]]
        elif re.match(r'leaveq?\b', text):
            residues['rsp'], residues['rbp'] = residues['rbp'], None
        elif re.match(r'popq\s+%rbp$', text):
            residues['rbp'] = None
        elif re.search(r',\s*%(rsp|rbp)$', text):
            residues[re.search(r'%(rsp|rbp)$', text)[1]] = None
        # pushq/popq change rsp by eight, so preserve its residue.
        broadcast = re.match(r'v(?:broadcasts([sd])|pbroadcast([dq]))\s+([^,]+),', text)
        operands = []
        if broadcast and '(' in broadcast[3]:
            size = 8 if broadcast[1] == 'd' or broadcast[2] == 'q' else 4
            operands.append((broadcast[3].strip(), size))
        # Folded broadcasts carry their element size in the memory decorator.
        # Keep indexed addresses intact so unsupported forms fail closed too.
        for folded in re.finditer(
                r'([^\s,{}()]*\([^)]*\)|[^\s,{}()]+)\s*\{1to(8|16)\}', text):
            operands.append((folded[1], 8 if folded[2] == '8' else 4))
        for operand, size in operands:
            constant = re.fullmatch(r'(\.LC[\w.]+)([+-]\d+)?\(%rip\)', operand)
            stack = re.fullmatch(r'(-?\d+)?\(%(rsp|rbp)\)', operand)
            if constant:
                known = constants.get(constant[1], 1)
                known = math.gcd(known, int(constant[2] or 0))
            elif stack and residues[stack[2]] is not None:
                known = math.gcd(8, residues[stack[2]] + int(stack[1] or 0))
            else:
                known = 1
            if known % size:
                failures.append('%s line %d: %s has only %d-byte proven alignment; needs %d'
                                % (function, number, text, known, size))
    return failures
