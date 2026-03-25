# Contributing to Qvantum Modbus Integration

Thank you for your interest in contributing to the Qvantum Modbus integration for Home Assistant! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Guidelines](#development-guidelines)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

This project follows the Home Assistant [Code of Conduct](https://www.home-assistant.io/code_of_conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

Key principles:

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the issue, not the person
- Help create a welcoming environment for all contributors

## Getting Started

### Prerequisites

- Home Assistant 2024.1.0 or newer
- Python 3.13 or newer
- Git
- A Qvantum heat pump with Modbus capability for testing (TCP or RTU)

### Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/majorfrog/qvantum_modbus.git
   cd qvantum_modbus
   ```

2. **Set up the Home Assistant development environment**
   - Follow the [Home Assistant development documentation](https://developers.home-assistant.io/docs/development_environment)
   - Or use a development Home Assistant instance

3. **Link to custom components**

   ```bash
   # Create symlink in your HA config directory
   ln -s /path/to/qvantum_modbus/custom_components/qvantum_modbus \
         /path/to/homeassistant/config/custom_components/
   ```

4. **Restart Home Assistant**
   - The integration should now be available

## How to Contribute

### Reporting Bugs

When reporting bugs, please include:

1. **Clear Title**: Descriptive summary of the issue
2. **Environment**:
   - Home Assistant version
   - Integration version
   - Modbus connection type (TCP or RTU)
   - Heat pump model
3. **Steps to Reproduce**: Detailed steps to recreate the issue
4. **Expected Behavior**: What should happen
5. **Actual Behavior**: What actually happens
6. **Logs**: Relevant log entries (with sensitive information removed)

**Template**:

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**Environment**

- Home Assistant version: 2025.1.0
- Integration version: 1.0.0
- Connection type: TCP / RTU
- Heat pump model: Qvantum HP

**To Reproduce**
Steps to reproduce the behavior:

1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
A clear description of what you expected to happen.

**Logs**

[Paste relevant log entries]
```

### Suggesting Features

Feature requests are welcome! Please:

1. **Check Existing Issues**: Search for similar requests first
2. **Provide Context**: Explain the use case
3. **Be Specific**: Describe the desired behavior
4. **Consider Scope**: Ensure it aligns with the integration's purpose

### Contributing Code

1. **Create a feature branch**

   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**
   - Follow the [Development Guidelines](#development-guidelines)
   - Add or update tests as needed
   - Update documentation

3. **Test your changes**
   - Test in a real Home Assistant instance if possible
   - Run the automated test suite (see [Testing](#testing))
   - Check logs for errors

4. **Commit your changes**

   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```

5. **Push to your fork**

   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a pull request**
   - Provide a clear description
   - Reference related issues
   - Include testing notes

## Development Guidelines

### Code Style

- **Python**: Follow [PEP 8](https://pep8.org/) style guide
- **Type hints**: Use type hints for all function arguments and return values
- **Docstrings**: Document all modules, classes, and functions
- **Line length**: Keep lines under 100 characters where reasonable
- **Naming**: Use descriptive variable and function names

### File Organization

- `__init__.py`: Integration setup and YAML schema validation
- `const.py`: All constants
- `models.py`: Data models (frozen dataclasses)
- `coordinator.py`: DataUpdateCoordinator with Modbus polling and backoff
- `entity.py`: Shared base entity class and `DeviceInfo` helper
- `sensor.py`: Sensor platform entities
- `config_flow.py`: UI configuration flow
- `strings.json`: User-facing text and translations

### Adding new sensors

Sensor definitions live in [`custom_components/qvantum_modbus/models.py`](custom_components/qvantum_modbus/models.py). Each sensor is a `ModbusSensorEntityDescription` entry in the `SENSOR_DESCRIPTIONS` tuple.

```python
ModbusSensorEntityDescription(
    key="qvantum_bt2",          # unique entity key
    translation_key="qvantum_bt2",
    address=1,                  # register address
    input_type=INPUT_TYPE_INPUT,  # INPUT_TYPE_INPUT (FC4) or INPUT_TYPE_HOLDING (FC3)
    data_type=DATA_TYPE_INT16,  # int16 / uint16 / int32 / uint32 / float32
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    scale=0.1,                  # multiply raw value by this
    precision=1,                # decimal places
),
```

After adding a new entry, also add its name translation to [`strings.json`](custom_components/qvantum_modbus/strings.json):

```json
"qvantum_bt2": {
  "name": "BT2 temperature"
}
```

No other files need to be changed — the coordinator and sensor platform pick up all entries from `SENSOR_DESCRIPTIONS` automatically.

### Logging

Use appropriate log levels:

- `_LOGGER.debug()`: Detailed diagnostic information
- `_LOGGER.info()`: Informational messages (e.g., device unavailable / recovered)
- `_LOGGER.warning()`: Warning messages
- `_LOGGER.error()`: Error messages

Never log sensitive information.

## Testing

### Automated Tests

The test suite uses the real Home Assistant test infrastructure. Tests must be
run inside the HA core virtual environment because they import from
`homeassistant` and `tests.common`.

#### One-time setup

1. **Clone Home Assistant core** (if you haven't already):

   ```bash
   git clone https://github.com/home-assistant/core.git /workspaces/core
   cd /workspaces/core
   pip install uv
   uv pip install -r requirements_test_all.txt -r requirements.txt
   ```

2. **Activate the HA virtual environment**:

   ```bash
   source /home/vscode/.local/ha-venv/bin/activate
   ```

   > The venv path may differ on your machine. Adjust as needed. You need
   > to activate it in every new terminal session before running tests.

#### Running the tests

```bash
# Activate the venv first (required every new terminal session)
source /home/vscode/.local/ha-venv/bin/activate

# Run all tests from the repo root
cd /home/vscode/repos/qvantum_modbus
pytest

# Run a specific file
pytest tests/test_coordinator.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=custom_components.qvantum_modbus --cov-report=term-missing
```

#### Running hassfest (integration structure validation)

`hassfest` checks that the integration structure, manifest, translations, and
service definitions are all valid:

```bash
cd /workspaces/core
python -m script.hassfest \
  --integration-path /home/vscode/repos/qvantum_modbus/custom_components/qvantum_modbus
```

### Manual Testing

1. **Install in a development Home Assistant**
   - Link or copy to `custom_components/qvantum_modbus`
   - Restart Home Assistant

2. **Test the configuration flow**
   - Add the integration through the UI
   - Verify TCP and RTU setup paths
   - Check that invalid host/port combinations are rejected

3. **Test entity creation**
   - Verify all expected sensor entities are created
   - Check that states and attributes are populated correctly

4. **Test error handling**
   - Test with the device offline — entities should become unavailable
   - Verify the coordinator applies exponential backoff on repeated failures
   - Verify recovery when the device comes back online

5. **Check logs**
   - Enable debug logging for `custom_components.qvantum_modbus`
   - Verify that unavailability and recovery are logged at `info` level (once each)
   - Confirm no sensitive data appears in logs

### Testing Checklist

Before submitting a PR, verify:

- [ ] Integration loads without errors
- [ ] Configuration flow works for both TCP and RTU
- [ ] All sensor entities are created
- [ ] Entity states update correctly
- [ ] Unavailability and recovery are handled gracefully
- [ ] Logs do not contain sensitive information
- [ ] No new warnings in Home Assistant logs
- [ ] All automated tests pass
- [ ] README.md is updated if there are user-facing changes

## Submitting Changes

### Pull Request Process

1. **Update documentation**
   - Update README.md for user-facing changes
   - Add docstrings to new code

2. **Self-review**
   - Review your own code first
   - Check for typos and formatting issues
   - Remove debug/console statements

3. **Create a pull request**
   - Use a descriptive title
   - Reference related issues (`#123`)
   - Describe what changed and why
   - Include testing notes

4. **Address review comments**
   - Respond to all review comments
   - Make requested changes
   - Request re-review when ready

### Commit Messages

Write clear, descriptive commit messages:

**Good**:

```
Add RTU parity configuration to config flow

- Add SelectSelector for parity (N/E/O)
- Update YAML schema to accept parity field
- Add tests for RTU parity validation

Fixes #42
```

**Bad**:

```
fix stuff
```

### Branch Naming

Use descriptive branch names:

- `feature/add-rtu-parity-support`
- `fix/sensor-unavailable-on-timeout`
- `refactor/coordinator-backoff`
