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
print('PASS host argument handling at densities 1-4; invalid arguments rejected')
