#!/usr/bin/env python3
"""Quick test runner to check integration tests."""

import sys
import subprocess

def main():
    """Run integration tests and report."""
    print("=" * 60)
    print("Testing Integration Pipeline (Task 5)")
    print("=" * 60)
    
    # Try to run tests
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", 
             "tests/integration/test_e2e_pipeline.py", 
             "-v", "--tb=short", "-x"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ ALL INTEGRATION TESTS PASSED!")
        else:
            print(f"❌ Tests failed with code {result.returncode}")
            print("\nFirst failure output above ↑")
        print("=" * 60)
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out (>60s)")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
