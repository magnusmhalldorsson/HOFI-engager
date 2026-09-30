#!/usr/bin/env python3
"""
Checkpointed CaDiCaL/LRAT driver, robust to process kills and container restarts.

Job directory segs/<job>/ contains F1.cnf (the original formula).  Segment i runs
    cadical --lrat --binary -t T  F<i>.cnf  seg<i>.lrat
When a segment ends without an answer (time limit, or killed by a restart), the valid prefix of
seg<i>.lrat is parsed, the clauses alive at its end that are not original clauses of F1 are
collected (length <= LMAX) into K<i>.cnf, cake_lpr verifies F<i> + seg<i> |- K<i>
("s VERIFIED TRANSFORMATION"), and F<i+1> = F1 + K<i>.  Every step of CaDiCaL's LRAT proof is a
RUP step with positive hints (checked while parsing), so every K<i> clause is implied by F1 and
unsatisfiability of any F<i> implies unsatisfiability of F1.  An UNSAT segment is verified by
cake_lpr ("s VERIFIED UNSAT").  Proof files are deleted after verification; their sha256 and the
checker output are kept in <job>/ledger.txt.
"""
import fcntl, hashlib, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
CADICAL = os.path.join(ROOT, 'tools/cadical/build/cadical')
CAKE = os.path.join(ROOT, 'tools/cake_lpr/cake_lpr')
LMAX = int(os.environ.get('LMAX', '40'))

def log(job, msg):
    with open(os.path.join(ROOT, 'segs', job, 'ledger.txt'), 'a') as f:
        f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')

def sha256(fn):
    h = hashlib.sha256()
    with open(fn, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def read_cnf(fn):
    cls = []; nv = 0
    with open(fn) as f:
        for line in f:
            if line[0] in 'pc':
                if line[0] == 'p': nv = int(line.split()[2])
                continue
            cls.append(list(map(int, line.split()[:-1])))
    return nv, cls

def parse_lrat(fn, m_input, out_trunc):
    """parse binary LRAT; return (alive derived+input dict id->lits, n_added, complete_bytes).
    Writes the longest prefix consisting of complete records to out_trunc."""
    data = open(fn, 'rb').read()
    n = len(data); i = 0; last_ok = 0
    added = {}; deleted = set(); nadd = 0
    def varint(i):
        x = 0; sh = 0
        while True:
            if i >= n: raise EOFError
            c = data[i]; i += 1
            x |= (c & 0x7f) << sh; sh += 7
            if c < 0x80: return x, i
    try:
        while i < n:
            t = data[i]; j = i + 1
            if t == 0x61:   # 'a'
                cid, j = varint(j); cid >>= 1
                lits = []
                while True:
                    x, j = varint(j)
                    if x == 0: break
                    lits.append(-(x >> 1) if x & 1 else (x >> 1))
                while True:
                    x, j = varint(j)
                    if x == 0: break
                    if x & 1: raise ValueError(f'negative (RAT) hint in clause {cid}')
                added[cid] = lits; nadd += 1
            elif t == 0x64: # 'd'
                ids = []
                while True:
                    x, j = varint(j)
                    if x == 0: break
                    ids.append(x >> 1)
                for d in ids:
                    if d in added: del added[d]
                    else: deleted.add(d)
            else:
                raise ValueError(f'bad record tag {t} at byte {i}')
            i = j; last_ok = i
    except EOFError:
        pass
    with open(out_trunc, 'wb') as f:
        f.write(data[:last_ok])
    return added, deleted, nadd, last_ok, n

def cake(args):
    """run cake_lpr under a global lock: one checker at a time keeps memory bounded"""
    with open(os.path.join(ROOT, 'segs', 'cake.lock'), 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        return subprocess.run([CAKE] + args, capture_output=True, text=True)

def run_segment(job, i, T):
    d = os.path.join(ROOT, 'segs', job)
    F = os.path.join(d, f'F{i}.cnf'); P = os.path.join(d, f'seg{i}.lrat'); L = os.path.join(d, f'seg{i}.log')
    cmd = [CADICAL, '--lrat=true', '--binary=true', '-t', str(T), '-f', F, P]
    with open(L, 'w') as lf:
        subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)

def process(job, i):
    """returns 'unsat', 'sat', or 'next'"""
    d = os.path.join(ROOT, 'segs', job)
    F = os.path.join(d, f'F{i}.cnf'); P = os.path.join(d, f'seg{i}.lrat'); L = os.path.join(d, f'seg{i}.log')
    out = open(L).read() if os.path.exists(L) else ''
    if 's UNSATISFIABLE' in out:
        r = cake([F, P])
        log(job, f'seg{i}: UNSAT; proof sha256 {sha256(P)} size {os.path.getsize(P)}; cake_lpr: {r.stdout.strip()}')
        if 's VERIFIED UNSAT' in r.stdout:
            json.dump({'status': 'unsat', 'seg': i}, open(os.path.join(d, 'state.json'), 'w'))
            return 'unsat'
        log(job, f'seg{i}: VERIFICATION FAILED'); raise SystemExit(2)
    if 's SATISFIABLE' in out:
        log(job, f'seg{i}: SATISFIABLE (relaxation) -- model in {L}')
        json.dump({'status': 'sat', 'seg': i}, open(os.path.join(d, 'state.json'), 'w'))
        return 'sat'
    # unfinished: extract lemmas (C extractor; checks there are no RAT hints)
    m1 = int(open(os.path.join(d, 'F1.m')).read())
    nv = int(open(os.path.join(d, 'F1.nv')).read())
    Ptr = os.path.join(d, f'seg{i}.trunc.lrat'); Kf = os.path.join(d, f'K{i}.cnf')
    x = subprocess.run([os.path.join(ROOT, 'lratx'), P, F, str(m1), str(LMAX), Ptr, Kf, str(nv)],
                       capture_output=True, text=True)
    if x.returncode != 0:
        log(job, f'seg{i}: extractor failed rc={x.returncode}: {x.stderr.strip()}'); raise SystemExit(2)
    r = cake([F, Ptr, Kf])
    ver = (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()) + f' (rc={r.returncode})'
    log(job, f'seg{i}: unfinished; {x.stdout.strip()}; proof sha256 {sha256(Ptr)}; cake_lpr: {ver}')
    if 's VERIFIED TRANSFORMATION' not in r.stdout:
        log(job, f'seg{i}: TRANSFORMATION VERIFICATION FAILED'); raise SystemExit(2)
    nk = int(open(Kf).readline().split()[3])
    Fn = os.path.join(d, f'F{i+1}.cnf')
    with open(Fn + '.tmp', 'w') as f:
        f.write(f'p cnf {nv} {m1 + nk}\n')
        with open(os.path.join(d, 'F1.cnf')) as g:
            for line in g:
                if line[0] not in 'pc': f.write(line)
        with open(Kf) as g:
            for line in g:
                if line[0] not in 'pc': f.write(line)
    os.replace(Fn + '.tmp', Fn)
    json.dump({'status': 'running', 'seg': i + 1}, open(os.path.join(d, 'state.json'), 'w'))
    for fn in (P, Ptr) + ((F,) if i > 1 else ()):
        if os.path.exists(fn): os.remove(fn)
    return 'next'

def job_loop(job, T):
    d = os.path.join(ROOT, 'segs', job)
    st = json.load(open(os.path.join(d, 'state.json'))) if os.path.exists(os.path.join(d, 'state.json')) else {'status': 'running', 'seg': 1}
    if st['status'] != 'running': return st['status']
    i = st['seg']
    while True:
        P = os.path.join(d, f'seg{i}.lrat')
        if not os.path.exists(P):
            log(job, f'seg{i}: start (T={T}s) on F{i} ({os.path.getsize(os.path.join(d, f"F{i}.cnf"))} bytes)')
            run_segment(job, i, T)
        else:
            log(job, f'seg{i}: found existing proof (previous run interrupted); processing')
        res = process(job, i)
        if res != 'next': return res
        i += 1

if __name__ == '__main__':
    job, T = sys.argv[1], int(sys.argv[2])
    print(job_loop(job, T))
