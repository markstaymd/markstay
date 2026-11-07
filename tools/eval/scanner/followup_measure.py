import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

path = Path(__file__).resolve().parents[2] / 'linter/markstay_lint.py'
spec = importlib.util.spec_from_file_location('scanner_followup', path)
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)

def measure(fn):
    start = time.perf_counter()
    result = fn()
    return round(time.perf_counter() - start, 6), result

for n in (500, 1000, 2000):
    text = ''.join(f'- item {i} <!--stay:c{i} subhash=sha256:aa -->\n' for i in range(n))
    no_child_time, no_children = measure(lambda: M.parse_document(text, child_blocks=False))
    child_time, blocks = measure(lambda: M.parse_document(text, child_blocks=True))
    assert len(blocks) == 1 and len(blocks[0].children) == n
    print(json.dumps({'case': 'child_ownership', 'n': n, 'input_chars': len(text), 'seconds_without_children': no_child_time, 'seconds_with_children': child_time}), flush=True)

for n in (500, 1000, 2000):
    text = '| ' + '<!--stay:x a=' * n + 'tail --> |'
    scan_time, records = measure(lambda: M._scan_marker_records(text))
    assert len(records) == n
    row_time, cells = measure(lambda: M._row_cells(text))
    assert cells is None
    refused_time, refused = measure(lambda: M._row_refused_marker_lines(text, set()))
    assert refused == {1}
    with patch.object(M, '_scan_marker_records', return_value=records):
        cached_row_time, _ = measure(lambda: M._row_cells(text))
        cached_refused_time, _ = measure(lambda: M._row_refused_marker_lines(text, set()))
    print(json.dumps({'case': 'row_overlap', 'n': n, 'input_chars': len(text), 'raw_output_chars': sum(len(r.marker.raw) for r in records), 'seconds_scanner': scan_time, 'seconds_row_cells': row_time, 'seconds_refused_lines': refused_time, 'seconds_row_cells_cached_records': cached_row_time, 'seconds_refused_lines_cached_records': cached_refused_time}), flush=True)
