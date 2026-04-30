# Testing Documentation

## Overview

This repository has comprehensive test coverage for all major components. Tests are automatically run on every push and pull request via GitHub Actions.

## Test Structure

```
tests/
├── conftest.py                          # Pytest fixtures and utilities
├── test_config.py                       # Configuration for tests
├── test_image_utils.py                  # Image utility tests
├── test_ruler_detector.py               # Ruler detection tests
├── test_ruler_detector_iraq_museum.py   # Iraq Museum ruler tests
├── test_manual_ruler_gui.py             # Manual ruler GUI tests
├── test_workflow_scale_detection.py     # Scale detection workflow tests
├── test_stitch_images.py                # Image stitching tests
├── test_measurements_utils.py           # Measurement utility tests
├── test_object_extractor.py             # Object extraction tests
├── test_version_checker.py              # Version checking tests
└── test_workflow.py                     # Complete workflow tests
```

## Running Tests

### Quick Start

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

Run all tests:
```bash
# Windows
run_tests.bat

# Unix/Mac
./run_tests.sh
```

### Test Modes

#### 1. All Tests (with coverage)
```bash
python run_tests.py --mode all
```

#### 2. Unit Tests Only
```bash
python run_tests.py --mode unit
```

#### 3. Integration Tests Only
```bash
python run_tests.py --mode integration
```

#### 4. Quick Tests (fast unit tests)
```bash
python run_tests.py --mode quick
```

#### 5. Full Coverage Report
```bash
python run_tests.py --mode coverage
```
This generates:
- HTML report: `htmlcov/index.html`
- XML report: `coverage.xml`
- Terminal output with missing lines

#### 6. Specific Test File
```bash
python run_tests.py --mode specific --file test_ruler_detector.py
```

### Advanced Options

Run tests in parallel:
```bash
python run_tests.py --mode all -n 4
```

Run with verbose output:
```bash
python run_tests.py --mode all -v
```

Run specific markers:
```bash
python run_tests.py --markers "ruler_detection"
```

### Using pytest directly

You can also use pytest directly for more control:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=lib --cov-report=html

# Run specific test markers
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "ruler_detection"
pytest tests/ -m "slow"

# Run specific test file
pytest tests/test_ruler_detector.py

# Run specific test function
pytest tests/test_ruler_detector.py::TestRulerDetector::test_detect_1cm_distance_with_valid_ruler

# Run with specific verbosity
pytest tests/ -vv

# Run in parallel (requires pytest-xdist)
pytest tests/ -n 4

# Stop on first failure
pytest tests/ -x

# Show local variables in tracebacks
pytest tests/ -l
```

## Test Markers

Tests are organized with markers for selective execution:

- `unit` - Unit tests for individual functions
- `integration` - Integration tests for module interactions
- `gui` - GUI-related tests (may require display)
- `slow` - Tests that take significant time to run
- `requires_images` - Tests that require sample images
- `ruler_detection` - Tests for ruler detection algorithms
- `image_processing` - Tests for image processing functions
- `workflow` - Tests for complete workflow processing

Example usage:
```bash
# Run only fast unit tests
pytest tests/ -m "unit and not slow"

# Run all ruler detection tests
pytest tests/ -m "ruler_detection"

# Run integration tests excluding GUI
pytest tests/ -m "integration and not gui"
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to main/master/develop branches
- Pull requests to main/master/develop
- Manual workflow dispatch

The CI pipeline:
1. Runs tests on multiple OS (Ubuntu, Windows, macOS)
2. Tests multiple Python versions (3.9, 3.10, 3.11)
3. Runs linting checks (flake8, black, isort)
4. Generates coverage reports
5. Uploads artifacts for debugging

View test results:
- Go to Actions tab in GitHub repository
- Click on the latest workflow run
- View test results and download coverage reports

### Pre-commit Hook (Optional)

To run tests before every commit, add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python run_tests.py --mode quick
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Writing New Tests

### Basic Test Structure

```python
import pytest
import sys
import os

# Add lib to path
lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from your_module import your_function


@pytest.mark.unit
class TestYourModule:
    """Test suite for your_module."""
    
    def test_your_function_success(self):
        """Test your_function with valid input."""
        result = your_function(valid_input)
        assert result == expected_output
    
    def test_your_function_error(self):
        """Test your_function with invalid input."""
        with pytest.raises(ValueError):
            your_function(invalid_input)
```

### Using Fixtures

```python
def test_with_temp_directory(temp_dir):
    """Use the temp_dir fixture."""
    output_file = temp_dir / "output.txt"
    # Your test code here
    assert output_file.exists()


def test_with_sample_image(sample_image):
    """Use the sample_image fixture."""
    assert sample_image.shape == (600, 800, 3)
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    """Test doubling function with multiple inputs."""
    assert double(input) == expected
```

## Coverage Goals

Target coverage: **80%+** for core modules

Current coverage by module:
- Run `python run_tests.py --mode coverage` to see current coverage
- Open `htmlcov/index.html` for detailed report

Priority modules for testing:
1. `ruler_detector.py` - Critical for scale detection
2. `workflow_scale_detection.py` - Core workflow
3. `stitch_images.py` - Main stitching logic
4. `object_extractor.py` - Object extraction
5. `manual_ruler_gui.py` - Manual measurement feature

## Troubleshooting

### GUI Tests Fail

GUI tests require a display. On headless systems:
```bash
# Skip GUI tests
pytest tests/ -m "not gui"
```

### Import Errors

Ensure lib directory is in Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:./lib"
```

### Missing Dependencies

Install all test dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Slow Tests

Skip slow tests for faster iteration:
```bash
pytest tests/ -m "not slow"
```

## Best Practices

1. **Write tests for new features** - Every new feature should have tests
2. **Run tests before committing** - Use `run_tests.py --mode quick`
3. **Check coverage** - Aim for 80%+ coverage on new code
4. **Use markers** - Mark tests appropriately (unit, integration, slow, etc.)
5. **Mock external dependencies** - Use `pytest-mock` for external services
6. **Keep tests fast** - Unit tests should run in seconds
7. **Test edge cases** - Include error conditions and boundary cases

## Continuous Improvement

After implementing a new feature:

1. Write unit tests for new functions
2. Write integration tests for workflows
3. Run full test suite: `python run_tests.py --mode all`
4. Check coverage: `python run_tests.py --mode coverage`
5. Ensure CI passes before merging

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
