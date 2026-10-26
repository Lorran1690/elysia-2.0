"""A Windows checkout must preserve the exact bytes protected by browser SRI."""
import base64
import hashlib
import re

from interface.server import WEB


def test_all_script_integrity_hashes_match_checked_out_bytes():
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    protected = re.findall(r'<script src="([^"]+)" integrity="sha384-([^"]+)"', html)
    assert len(protected) == 3
    for path, expected in protected:
        actual = base64.b64encode(hashlib.sha384((WEB / path).read_bytes()).digest()).decode()
        assert actual == expected, f'Browser would block {path}; check newline conversion'
