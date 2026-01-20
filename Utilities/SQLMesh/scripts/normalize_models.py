#!/usr/bin/env python3
import re, os, sys
root = os.path.join(os.path.dirname(__file__), '..', 'models', 'staging')
root = os.path.normpath(root)
files = [os.path.join(root, f) for f in os.listdir(root) if f.endswith('.sql')]
changed = []
for p in files:
    with open(p, 'r', encoding='utf-8') as f:
        txt = f.read()
    orig = txt
    # remove markdown fences
    txt = re.sub(r"^```sql\s*\n", '', txt, flags=re.M)
    txt = re.sub(r"\n```\s*$", '\n', txt, flags=re.M)
    # fix duplicate comma
    txt = txt.replace('),,', '),')
    # canonicalize grain lines like: grain col,  -> grain (col),
    txt = re.sub(r'(?m)^(\s*grain)\s+([A-Za-z0-9_, ]+),\s*$', lambda m: f"{m.group(1)} ({m.group(2).strip()}),", txt)
    # normalize MODEL blocks and audits trailing comma
    out = []
    i = 0
    L = len(txt)
    while i < L:
        si = txt.find('MODEL (', i)
        if si == -1:
            out.append(txt[i:])
            break
        out.append(txt[i:si])
        # find opening paren pos
        open_pos = txt.find('(', si)
        if open_pos == -1:
            # malformed, bail
            out.append(txt[si:])
            break
        j = open_pos + 1
        depth = 1
        while j < L and depth > 0:
            if txt[j] == '(':
                depth += 1
            elif txt[j] == ')':
                depth -= 1
            j += 1
        if depth != 0:
            # couldn't match, append rest and stop
            out.append(txt[si:])
            break
        # j is index after the matching ')'
        # capture until the following ';' (end of MODEL block)
        k = j
        while k < L and txt[k].isspace():
            k += 1
        if k < L and txt[k] == ';':
            end_idx = k+1
        else:
            # try find next ';' within small window
            sc = txt.find(';', j)
            end_idx = sc+1 if sc != -1 else j
        block = txt[si:end_idx]
        # process audits inside block
        a = block.find('audits (')
        if a != -1:
            # find audits matching paren
            aa = block.find('(', a)
            jj = aa + 1
            d2 = 1
            while jj < len(block) and d2 > 0:
                if block[jj] == '(':
                    d2 += 1
                elif block[jj] == ')':
                    d2 -= 1
                jj += 1
            if d2 == 0:
                close_idx = jj - 1
                # text after audits closing paren within block
                after = block[close_idx+1:].lstrip() if close_idx+1 < len(block) else ''
                # determine if there are other keys before model end (i.e., after not starting with ');')
                has_more = True
                if after == '' or after.startswith(');'):
                    has_more = False
                # find start of the audits closing line
                line_start = block.rfind('\n', 0, close_idx) + 1
                line_end = block.find('\n', close_idx)
                if line_end == -1:
                    line_end = len(block)
                line = block[line_start:line_end]
                new_line = line.rstrip()
                if has_more:
                    if not new_line.endswith('),'):
                        new_line = new_line.rstrip(' ,') + '),'
                else:
                    new_line = new_line.rstrip(' ,') + ')'
                block = block[:line_start] + new_line + block[line_end:]
                # remove accidental double close patterns
                block = re.sub(r"\),\s*\),", "),", block)
        # ensure block ends with ');' spacing
        block = re.sub(r"\)\s*,?\s*;\s*$", ");", block)
        out.append(block)
        i = end_idx
    newtxt = ''.join(out)
    if newtxt != orig:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(newtxt)
        changed.append(p)
print('Modified files:')
for c in changed:
    print('-', c)
if not changed:
    print('None')
