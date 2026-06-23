"""Put the example's own directory on the path so its local modules
(``chunker``, ``cache``, ``langchain_adapter``, ``demo``) import regardless of
pytest's collection order. ``markstay`` itself comes from the installed package
(``pip install markstay``), not a path.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
