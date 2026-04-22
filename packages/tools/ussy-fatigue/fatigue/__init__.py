"""Fatigue — Fracture Mechanics for Code Decay Prediction.

Applies Paris' Law of fatigue crack growth to model and predict code decay.
Detects cracks (flaws, workarounds, tech debt markers), measures stress
intensity (coupling × change frequency × complexity), models crack growth
rate using a Paris' Law-derived equation, and predicts time-to-failure
for each module.
"""

__version__ = "1.0.0"

# Default material constants
DEFAULT_C = 0.015  # crack growth coefficient
DEFAULT_M = 2.5    # stress exponent (moderately brittle)

# Default thresholds
DEFAULT_K_IC = 28.0   # fracture toughness
DEFAULT_K_E = 8.2     # endurance limit
