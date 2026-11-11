import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'tools'))
import s9_18_pgo

def test_parse_busybox_od_b():
    text = 'GCDA a.gcda\n0000000 141 144 143 147 001 002\n0000006\nEND\n'
    assert s9_18_pgo.parse_gcda(text) == {'a.gcda': b'adcg\x01\x02'}
