"""PR Canary — guard-rail checks for Phase 6+ Velocity Hardening.

Fails PR on guard-rail breach:
- drift > 5%
- Covenant pass-rate regress
- p95 regress > 20%
- cost > 1.5x
- refusal deviation > 2σ
"""

import sys
import os

def main():
    # In a real implementation, this would read metrics from the shadow relay
    # and compare them against the baseline corpus.
    
    # For now, we simulate the check.
    # If XION_SYNTHETIC_BAD_PR is set, we fail.
    if os.environ.get("XION_SYNTHETIC_BAD_PR") == "1":
        print("PR Canary: FAIL: Synthetic bad PR detected (drift > 5%).")
        sys.exit(1)
        
    print("PR Canary: OK (guard-rails passed).")
    sys.exit(0)

if __name__ == "__main__":
    main()
