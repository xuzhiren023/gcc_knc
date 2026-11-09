"""Host-only argument acceptance; never execute a timing kernel."""
import subprocess
import sys
from pathlib import Path

binary = Path(sys.argv[1])
assert binary.is_file(), 'missing host dry-run executable'
for density in range(1, 5):
    result = subprocess.run([str(binary), '--dry-run', '--threads', str(density)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'vaddps.lat' in result.stdout and 'memory.store_stream' in result.stdout
    assert 'DRY' in result.stdout
for args in ([], ['--threads', '0'], ['--threads', '5'], ['--threads'],
             ['--threads', '2junk'], ['--rounds', '-1'], ['--unknown'],
             ['--dry-run', '--case', 'nonexistent'], ['--native']):
    result = subprocess.run([str(binary), *args], capture_output=True, text=True)
    assert result.returncode != 0, args
# S8-10 C11: seven named points in a dry run; native needs two cores.
result = subprocess.run([str(binary), '--dry-run', '--check', 'c11', '--cores', '60', '--threads', '4'],
                        capture_output=True, text=True)
assert result.returncode == 0, result.stderr
names = [line.split()[1] for line in result.stdout.splitlines() if line.startswith('DRY ')]
assert names == ['c11.l2.local', 'c11.l2.remote.near', 'c11.l2.remote.far', 'c11.pingpong.shared',
                 'c11.pingpong.padded', 'c11.barrier.counter', 'c11.barrier.tree'], names
for args in (['--dry-run', '--check', 'c11', '--case', 'c11.none'],
             ['--dry-run', '--check', 'c11', '--threads', '3'],
             ['--native', '--check', 'c11', '--cores', '1']):
    result = subprocess.run([str(binary), *args], capture_output=True, text=True)
    assert result.returncode != 0, args
print('PASS host argument handling at densities 1-4; invalid arguments rejected')
