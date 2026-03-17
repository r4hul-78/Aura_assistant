"""
Tests for the AudioFileManager — standalone, no EventBus/TTS required.

Validates:
1. Unique path generation (no collisions under rapid calls)
2. Correct .wav extension
3. Registry tracking
4. Cleanup removes existing files, skips missing ones
5. Output directory configuration
"""

import os
import sys
import tempfile

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aura.core.audio_file_manager import AudioFileManager  # pyre-ignore[21]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COUNTS = {"passed": 0, "failed": 0}


def check(label: str, condition: bool, detail: str = ""):
    """Simple assertion with formatted output."""
    status = "PASS" if condition else "FAIL"
    if condition:
        _COUNTS["passed"] += 1
    else:
        _COUNTS["failed"] += 1
    extra = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{extra}")


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

def test_unique_paths():
    """100 rapid generate() calls must produce 100 distinct paths."""
    print("\n--- Test: Unique Path Generation ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = AudioFileManager(output_dir=tmpdir)
        paths = [mgr.generate() for _ in range(100)]
        unique = set(paths)
        check("100 calls → 100 unique paths", len(unique) == 100,
              f"got {len(unique)} unique out of 100")


def test_wav_extension():
    """All generated paths must end with .wav."""
    print("\n--- Test: File Extension ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = AudioFileManager(output_dir=tmpdir)
        paths = [mgr.generate() for _ in range(10)]
        all_wav = all(p.endswith(".wav") for p in paths)
        check("All paths end in .wav", all_wav)


def test_registry_tracking():
    """Generated paths must appear in the registry."""
    print("\n--- Test: Registry Tracking ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = AudioFileManager(output_dir=tmpdir)
        p1 = mgr.generate()
        p2 = mgr.generate()
        check("p1 in registry", p1 in mgr.registry)
        check("p2 in registry", p2 in mgr.registry)
        check("Registry size is 2", len(mgr.registry) == 2,
              f"size={len(mgr.registry)}")


def test_cleanup_deletes_files():
    """cleanup() should delete existing tracked files."""
    print("\n--- Test: Cleanup Deletes Files ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = AudioFileManager(output_dir=tmpdir)
        paths = [mgr.generate() for _ in range(5)]

        # Create actual files to simulate TTS output
        for p in paths:
            with open(p, "wb") as f:
                f.write(b"\x00" * 100)

        check("Files exist before cleanup",
              all(os.path.exists(p) for p in paths))

        mgr.cleanup()

        check("Files deleted after cleanup",
              not any(os.path.exists(p) for p in paths))
        check("Registry cleared", len(mgr.registry) == 0)


def test_cleanup_handles_missing_files():
    """cleanup() should not raise when files are already gone."""
    print("\n--- Test: Cleanup Skips Missing Files ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = AudioFileManager(output_dir=tmpdir)
        mgr.generate()  # Never actually written to disk

        try:
            mgr.cleanup()
            check("No error on missing files", True)
        except Exception as e:
            check("No error on missing files", False, str(e))


def test_output_directory():
    """Files should be generated under the configured output directory."""
    print("\n--- Test: Output Directory ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        subdir = os.path.join(tmpdir, "custom_out")
        mgr = AudioFileManager(output_dir=subdir)
        path = mgr.generate()

        check("Output dir was created", os.path.isdir(subdir))
        check("Path is under output dir", path.startswith(subdir), path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 55)
    print("   AudioFileManager Test Suite")
    print("=" * 55)

    test_unique_paths()
    test_wav_extension()
    test_registry_tracking()
    test_cleanup_deletes_files()
    test_cleanup_handles_missing_files()
    test_output_directory()

    print("\n" + "=" * 55)
    print(f"   Results: {_COUNTS['passed']} passed, {_COUNTS['failed']} failed")
    print("=" * 55)

    if _COUNTS["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
