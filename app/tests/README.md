# Alice Is Missing - Test Suite

## Overview
This directory contains the automated test suite for the Alice Is Missing game application. The tests ensure proper functionality of game mechanics, player interactions, and messaging systems.

## Directory Structure

```
tests/
├── chat/                 # Chat and messaging tests
│   └── test_messaging.py # Tests for messaging system
├── game/                 # Game mechanics tests
│   ├── test_characters.py # Tests for character cards
│   └── test_messages.py  # Tests for game messages
└── players/             # Player management tests
    └── test_players.py  # Tests for player functionality
```

## Running Tests

### Using the Test Runner Script
The recommended way to run tests is using the provided script:
```bash
./run_tests.sh
```

This will:
- Run all tests with coverage reporting
- Generate detailed test reports
- Create coverage reports in HTML and text formats

### Manual Test Execution
You can also run tests manually using these commands:

1. Run all tests:
```bash
poetry run python manage.py test tests/ --settings=tests.settings -v 2
```

2. Run specific test modules:
```bash
# Run chat tests
poetry run python manage.py test tests.chat --settings=tests.settings

# Run game tests
poetry run python manage.py test tests.game --settings=tests.settings

# Run player tests
poetry run python manage.py test tests.players --settings=tests.settings
```

## Test Reports

Test results and coverage reports are saved in the following locations:
- Test execution report: `reports/test_report_[TIMESTAMP].txt`
- Coverage HTML report: `reports/htmlcov/index.html`
- Console output with real-time test results

## Writing Tests

### Test Case Structure
Follow these guidelines when writing new tests:

1. Place tests in the appropriate module directory
2. Use descriptive test method names
3. Include docstrings explaining test purpose
4. Set up required test data in setUp()
5. Clean up resources in tearDown() if needed

Example:
```python
def test_message_creation(self):
    """Test creation of a basic game message"""
    message = Message.objects.create(
        game=self.game,
        sender=self.player,
        content='Test message'
    )
    self.assertEqual(message.content, 'Test message')
```

### Test Categories
- Unit Tests: Test individual model methods
- Integration Tests: Test interaction between components
- Functional Tests: Test complete game features

## Test Settings

The test suite uses a specific settings file (`tests/settings.py`) that configures:
- In-memory SQLite database
- Fast password hasher
- Disabled migrations
- Test-specific static/media handling

## Contributing

When adding new tests:
1. Follow the existing directory structure
2. Add appropriate documentation
3. Ensure tests are isolated and independent
4. Include both positive and negative test cases
5. Verify coverage for new code

## Troubleshooting

Common issues and solutions:
1. Test database errors:
   - Ensure migrations are up to date
   - Check database settings
2. Import errors:
   - Verify correct module paths
   - Check for circular imports
3. Coverage reporting issues:
   - Ensure .coveragerc is present
   - Check write permissions for reports directory

