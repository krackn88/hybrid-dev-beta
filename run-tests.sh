#!/bin/bash
# Automated Testing Script for hybrid-dev-beta
# Version: 1.0.0

# ===== CONFIGURATION =====
REPO_DIR="${HOME}/hybrid-dev-beta"
TEST_DIR="${REPO_DIR}/tests"
EXTENSION_DIR="${REPO_DIR}/vscode-extension"
LOG_FILE="${REPO_DIR}/testing.log"
REPORT_DIR="${REPO_DIR}/test-reports"

# ===== FORMATTING =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== LOGGING FUNCTIONS =====
log() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_success() { log "${GREEN}SUCCESS: $1${NC}"; }
log_info() { log "${BLUE}INFO: $1${NC}"; }
log_warning() { log "${YELLOW}WARNING: $1${NC}"; }
log_error() { log "${RED}ERROR: $1${NC}"; }

# ===== TEST FUNCTIONS =====
run_python_tests() {
    log_info "Running Python tests..."
    
    if [ -d "${TEST_DIR}/python" ]; then
        cd "${TEST_DIR}/python"
        
        # Check for pytest
        if command -v pytest &> /dev/null; then
            mkdir -p "${REPORT_DIR}/python"
            pytest --junitxml="${REPORT_DIR}/python/results.xml"
            
            if [ $? -eq 0 ]; then
                log_success "Python tests passed"
                return 0
            else
                log_error "Python tests failed"
                return 1
            fi
        else
            log_warning "pytest not found, falling back to unittest"
            python -m unittest discover
            
            if [ $? -eq 0 ]; then
                log_success "Python tests passed"
                return 0
            else
                log_error "Python tests failed"
                return 1
            fi
        fi
    else
        log_info "No Python tests directory found, skipping"
        return 0
    fi
}

run_vscode_extension_tests() {
    log_info "Running VSCode extension tests..."
    
    if [ -d "$EXTENSION_DIR" ]; then
        cd "$EXTENSION_DIR"
        
        # Install dependencies if needed
        if [ ! -d "node_modules" ]; then
            npm install --quiet
        fi
        
        # Run tests if test script exists in package.json
        if grep -q '"test":' package.json; then
            mkdir -p "${REPORT_DIR}/vscode-extension"
            npm test
            
            if [ $? -eq 0 ]; then
                log_success "VSCode extension tests passed"
                return 0
            else
                log_error "VSCode extension tests failed"
                return 1
            fi
        else
            log_warning "No test script found in package.json, skipping extension tests"
            return 0
        fi
    else
        log_info "VSCode extension directory not found, skipping extension tests"
        return 0
    fi
}

run_integration_tests() {
    log_info "Running integration tests..."
    
    if [ -d "${TEST_DIR}/integration" ]; then
        cd "${TEST_DIR}/integration"
        
        # Look for custom integration test script
        if [ -f "run_tests.sh" ]; then
            chmod +x run_tests.sh
            ./run_tests.sh
            
            if [ $? -eq 0 ]; then
                log_success "Integration tests passed"
                return 0
            else
                log_error "Integration tests failed"
                return 1
            fi
        else
            log_warning "No integration test runner found, skipping"
            return 0
        fi
    else
        log_info "No integration tests directory found, skipping"
        return 0
    fi
}

generate_test_report() {
    log_info "Generating test report..."
    
    # Create report directory
    mkdir -p "$REPORT_DIR"
    
    # Create HTML report
    cat > "${REPORT_DIR}/index.html" << EOL
<!DOCTYPE html>
<html>
<head>
    <title>Hybrid Dev Beta - Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        h1 { color: #333; }
        .test-group { margin-bottom: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .test-group h2 { margin-top: 0; }
        .success { color: green; }
        .failure { color: red; }
        .warning { color: orange; }
        .timestamp { color: #666; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>Hybrid Dev Beta - Test Report</h1>
    <p class="timestamp">Generated on: $(date)</p>
    
    <div class="test-group">
        <h2>Test Summary</h2>
        <p>Python Tests: $(grep -q "Python tests passed" "$LOG_FILE" && echo "<span class='success'>Passed</span>" || echo "<span class='failure'>Failed</span>")</p>
        <p>VSCode Extension Tests: $(grep -q "VSCode extension tests passed" "$LOG_FILE" && echo "<span class='success'>Passed</span>" || echo "<span class='failure'>Failed</span>")</p>
        <p>Integration Tests: $(grep -q "Integration tests passed" "$LOG_FILE" && echo "<span class='success'>Passed</span>" || echo "<span class='warning'>Skipped/Failed</span>")</p>
    </div>
    
    <div class="test-group">
        <h2>Log Highlights</h2>
        <pre>$(grep -E "ERROR|SUCCESS|WARNING" "$LOG_FILE" | tail -20)</pre>
    </div>
</body>
</html>
EOL
    
    log_success "Test report generated at ${REPORT_DIR}/index.html"
}

# ===== MAIN EXECUTION =====
main() {
    # Initialize log
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "=== Test Run - $(date) ===" > "$LOG_FILE"
    
    log_info "Starting test suite"
    
    # Create test directories if they don't exist
    mkdir -p "$TEST_DIR"
    mkdir -p "${TEST_DIR}/python"
    mkdir -p "${TEST_DIR}/integration"
    
    # Run all tests
    local test_results=0
    
    run_python_tests
    test_results=$((test_results + $?))
    
    run_vscode_extension_tests
    test_results=$((test_results + $?))
    
    run_integration_tests
    test_results=$((test_results + $?))
    
    # Generate report
    generate_test_report
    
    # Output summary
    if [ $test_results -eq 0 ]; then
        log_success "All tests passed!"
    else
        log_error "$test_results test groups failed!"
    fi
    
    return $test_results
}

# Run main function
main