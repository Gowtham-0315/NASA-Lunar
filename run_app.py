"""Entrypoint to launch the Lunar Landing Site Intelligence web application."""

import sys
import os

# Set standard output encoding to utf-8 if possible
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure src is on python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print(">>> LUNAR LANDING SITE INTELLIGENCE PLATFORM <<<")
    print("=" * 70)
    print("Resources integrated:")
    print("  * LROC QuickMap:   https://quickmap.lroc.asu.edu/")
    print("  * NASA Moon Trek:  https://trek.nasa.gov/moon/")
    print("  * JPL Horizons:    https://ssd.jpl.nasa.gov/horizons/")
    print("  * CSA Moon Explor: https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/")
    print("=" * 70)
    print("Starting server on: http://127.0.0.1:8000")
    print("Open your browser and navigate to http://127.0.0.1:8000")
    print("=" * 70)
    uvicorn.run("lunar_intelligence.api:app", host="127.0.0.1", port=8000, reload=False)
