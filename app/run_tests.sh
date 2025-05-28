#!/bin/zsh

# Exit on error and undefined variables
set -eu

# Colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
CYAN="\033[0;36m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color
BOLD="\033[1m"

# Create reports directory if it doesn't exist
mkdir -p reports

# Generate timestamp for report
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
REPORT_FILE="reports/test_report_${TIMESTAMP}.txt"

# Function to log both to console and file
log() {
    local message="$1"
    echo -e "${message}" | tee -a "${REPORT_FILE}"
}

# Print header
log "Alice Is Missing - Test Execution Report"
log "======================================="
log "Date: $(date "+%Y-%m-%d %H:%M:%S")"
log "Python: $(poetry run python --version 2>&1)"
log "Django: $(poetry run python -c 'import django; print(django.get_version())' 2>&1)"
log "======================================="
log ""

# Check environment
if [[ ! -f "manage.py" ]]; then
    log "${RED}Error: manage.py not found. Please run this script from the Django project root directory.${NC}"
    exit 1
fi

# Clean up previous coverage data
log "${CYAN}Cleaning up previous coverage data...${NC}"
poetry run coverage erase

# Create coverage config if it doesn't exist
if [[ ! -f ".coveragerc" ]]; then
    log "${YELLOW}Creating coverage configuration...${NC}"
    cat > .coveragerc << EOL
[run]
source = game
omit =
    */tests/*
    */migrations/*
    manage.py
    */wsgi.py
    */asgi.py
    */settings.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
EOL
fi

# Run tests with coverage for each module
MODULES=("chat" "game" "players")
GLOBAL_STATUS=0

for module in "${MODULES[@]}"; do
    log "\n${BOLD}Running tests for ${module}${NC}"
    log "===================="
    
    if poetry run coverage run --append --source=game manage.py test "tests.${module}" --settings=tests.settings -v 2; then
        log "${GREEN}✓ Tests passed for ${module}${NC}"
    else
        log "${RED}✗ Tests failed for ${module}${NC}"
        GLOBAL_STATUS=1
    fi
done

# Generate coverage reports
log "\n${CYAN}Generating coverage reports...${NC}"
log "===================="

# Text coverage report
log "\nCoverage Summary:"
poetry run coverage report -m | tee -a "${REPORT_FILE}"

# HTML coverage report
poetry run coverage html -d reports/htmlcov
log "\nDetailed HTML coverage report: reports/htmlcov/index.html"

# Final summary
log "\n${BOLD}Test Execution Summary${NC}"
log "===================="
if [ $GLOBAL_STATUS -eq 0 ]; then
    log "${GREEN}✓ All tests completed successfully!${NC}"
else
    log "${RED}✗ Some tests failed!${NC}"
fi

log "\nTest Reports:"
log "- Execution Log: ${REPORT_FILE}"
log "- Coverage Report: reports/htmlcov/index.html"

exit $GLOBAL_STATUS

