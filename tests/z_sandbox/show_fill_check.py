"""show_fill_check.py -- fill_check.html as a doc of the report server (contactRS): one layout of blocks in plain divs, in a
flex row and in a table cell, to see in the browser which fill the page. The page opens in the default browser."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from reportserver import contactRS

got = contactRS('load', '[doc]', {'doc': ['doc', './mumix/tests/z_sandbox/fill_check.html']}, 'fill check', '--hidden' not in sys.argv)
print(got['url'])
