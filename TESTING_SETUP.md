# Quick Setup Guide for Testing

## Windows Setup

1. **Install test dependencies**
   ```cmd
   pip install -r requirements-test.txt
   ```

2. **Run tests**
   ```cmd
   run_tests.bat all
   ```
   Or:
   ```cmd
   python run_tests.py --mode all
   ```

## Unix/Mac Setup

1. **Install test dependencies**
   ```bash
   pip install -r requirements-test.txt
   ```

2. **Make test runner executable** (if needed)
   ```bash
   chmod +x run_tests.sh
   ```

3. **Run tests**
   ```bash
   ./run_tests.sh all
   ```
   Or:
   ```bash
   python run_tests.py --mode all
   ```

## Verify Installation

```bash
# Run quick tests to verify setup
python run_tests.py --mode quick
```

If all tests pass, your testing environment is ready! ✅

See [TESTING.md](TESTING.md) for comprehensive documentation.
