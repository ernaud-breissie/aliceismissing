#!/bin/zsh

# Exit on error, undefined variables, and print commands
set -eux

# Colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m" # No Color
BOLD="\033[1m"

echo "Debug: Current directory: $(pwd)"
echo "Debug: Listing directory contents:"
ls -la

# Create reports directory if it doesn't exist
mkdir -p reports

# Generate timestamp for report
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
REPORT_FILE="reports/test_report_${TIMESTAMP}.txt"

echo "Debug: Will write to file: ${REPORT_FILE}"

# Test modules based on project structure
MODULES=("chat" "game" "players")

# Function to log both to console and file
log() {
    local message="$1"
    echo -e "${message}" | tee -a "${REPORT_FILE}"
}

# Initialize report file with header
log "Test Report - $(date "+%Y-%m-%d %H:%M:%S")"
log "===================="

# Initialize global status
GLOBAL_STATUS=0

# Check Python and Poetry versions
echo "Debug: Python version:"
python --version
echo "Debug: Poetry version:"
poetry --version

# Check test files exist
echo "Debug: Checking test files:"
ls -R tests/

# Run tests for each module
for module in "${MODULES[@]}"; do
    echo "Debug: Processing module: ${module}"
    log "\n${BOLD}Running tests for ${module}${NC}"
    log "===================="
    
    echo "Debug: Running tests for ${module}"
    if poetry run python manage.py test "tests/${module}" --settings=tests.settings -v 2; then
        log "${GREEN}Tests passed for ${module}${NC}"
    else
        GLOBAL_STATUS=1
        log "${RED}Tests failed for ${module}${NC}"
    fi
done

# Final summary
log "\n${BOLD}Test Summary${NC}"
log "===================="
if [ $GLOBAL_STATUS -eq 0 ]; then
    log "${GREEN}All tests completed successfully!${NC}"
else
    log "${RED}Some tests failed!${NC}"
fi

log "\nReport saved to: ${REPORT_FILE}"

# Exit with proper status
exit $GLOBAL_STATUS
