import os
import sys
import datetime
import re

# Add the parent directory to sys.path to allow importing from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from games import ALL_CLASSES, generate_sample_update

# Gather all subclasses of Giochino that define examples
testable_games = [cls for cls in ALL_CLASSES if getattr(cls, "examples", None)]

# Flatten the structure into a list of tuples: (game_class, index, example_text, expected_dict)
test_cases = []
for cls in testable_games:
    for idx, (example, expected) in enumerate(zip(cls.examples, cls.expected)):
        test_cases.append((cls, idx, example, expected))


@pytest.mark.parametrize(
    "game_class, idx, example, expected",
    test_cases,
    ids=lambda case: f"{case[0]._name}_example_{case[1] + 1}"
)
def test_game_examples(game_class, idx, example, expected):
    # Generate the dummy update object from the example string
    update = generate_sample_update(example)
    
    # Instantiate the game class (which automatically calls parse())
    instance = game_class(update)
    
    if expected is None:
        assert instance.punteggio is None
    else:
        assert instance.punteggio is not None
        
        # Verify the parsed output matches all expected keys and values
        for key, val in expected.items():
            # Special case for timestamp since it's dynamically set to 10 in generate_sample_update
            if key == "timestamp":
                assert instance.punteggio.get(key) == 10
            else:
                assert instance.punteggio.get(key) == val
