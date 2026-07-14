#!/bin/bash

################################################################################
# Setup Guide Expert - Automated Setup Script
# 
# Purpose: Automate comprehensive application setup with expert guidance
# Usage: ./setup-guide-expert.sh [action]
# Actions: analyze, setup, verify, troubleshoot
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

################################################################################
# STEP 1: COMPREHENSIVE ANALYSIS
################################################################################
analyze_project() {
    log_info "Starting comprehensive project analysis..."
    
    # Check repository structure
    log_info "Examining repository structure..."
    find . -maxdepth 2 -type f -name "*.json" -o -name "*.txt" -o -name "*.yml" -o -name "*.yaml" | head -20
    
    # Check for dependency files
    log_info "Checking for dependency files..."
    
    if [ -f "package.json" ]; then
        log_success "Found package.json (Node.js/JavaScript project)"
    fi
    
    if [ -f "requirements.txt" ]; then
        log_success "Found requirements.txt (Python project)"
    fi
    
    if [ -f "pom.xml" ]; then
        log_success "Found pom.xml (Java/Maven project)"
    fi
    
    if [ -f "Gemfile" ]; then
        log_success "Found Gemfile (Ruby project)"
    fi
    
    if [ -f "Dockerfile" ]; then
        log_success "Found Dockerfile (Docker container setup)"
    fi
    
    if [ -f ".env.example" ]; then
        log_success "Found .env.example (configuration template)"
    fi
    
    if [ -f "README.md" ]; then
        log_success "Found README.md"
        log_info "README.md preview:"
        head -30 README.md
    fi
    
    # Check git history
    if git rev-parse --git-dir > /dev/null 2>&1; then
        log_success "Git repository detected"
        log_info "Recent commits:"
        git log --oneline -5 2>/dev/null || true
    fi
    
    log_success "Analysis complete!"
}

################################################################################
# STEP 2: DEPENDENCY MAPPING
################################################################################
check_dependencies() {
    log_info "Checking system dependencies..."
    
    # Node.js
    if command -v node &> /dev/null; then
        log_success "Node.js installed: $(node --version)"
    else
        log_warning "Node.js not found"
    fi
    
    # Python
    if command -v python3 &> /dev/null; then
        log_success "Python 3 installed: $(python3 --version)"
    else
        log_warning "Python 3 not found"
    fi
    
    # npm
    if command -v npm &> /dev/null; then
        log_success "npm installed: $(npm --version)"
    else
        log_warning "npm not found"
    fi
    
    # git
    if command -v git &> /dev/null; then
        log_success "Git installed: $(git --version)"
    else
        log_warning "Git not found"
    fi
    
    # Docker
    if command -v docker &> /dev/null; then
        log_success "Docker installed: $(docker --version)"
    else
        log_warning "Docker not found"
    fi
}

################################################################################
# STEP 3: SETUP EXECUTION
################################################################################
setup_nodejs_project() {
    log_info "Setting up Node.js project..."
    
    if [ ! -f "package.json" ]; then
        log_error "package.json not found!"
        return 1
    fi
    
    # Install dependencies
    log_info "Installing Node dependencies..."
    npm install || npm ci
    log_success "Node dependencies installed"
}

setup_python_project() {
    log_info "Setting up Python project..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found!"
        return 1
    fi
    
    # Create virtual environment
    log_info "Creating Python virtual environment..."
    python3 -m venv venv || python3 -m venv .venv
    
    # Activate and install
    log_info "Activating virtual environment..."
    source venv/bin/activate || source .venv/bin/activate
    
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt
    log_success "Python dependencies installed"
}

setup_env_files() {
    log_info "Setting up environment files..."
    
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        log_info "Creating .env from .env.example..."
        cp .env.example .env
        log_warning "⚠️  Edit .env with your configuration values!"
    fi
}

################################################################################
# STEP 4: VERIFICATION
################################################################################
verify_setup() {
    log_info "Verifying setup..."
    
    # Check Node.js project
    if [ -f "package.json" ]; then
        log_info "Verifying Node.js setup..."
        if [ -d "node_modules" ]; then
            log_success "node_modules directory exists"
        else
            log_error "node_modules not found - run 'npm install'"
        fi
    fi
    
    # Check Python project
    if [ -f "requirements.txt" ]; then
        log_info "Verifying Python setup..."
        if [ -d "venv" ] || [ -d ".venv" ]; then
            log_success "Virtual environment exists"
        else
            log_error "Virtual environment not found - run setup first"
        fi
    fi
    
    # Check configuration
    if [ -f ".env" ]; then
        log_success ".env configuration file exists"
    elif [ -f ".env.example" ]; then
        log_warning ".env not found - copy from .env.example and configure"
    fi
    
    log_success "Verification complete!"
}

################################################################################
# STEP 5: TROUBLESHOOTING
################################################################################
troubleshoot() {
    log_info "Running troubleshooting checks..."
    
    log_info "\n=== System Information ==="
    uname -a
    
    log_info "\n=== Installed Versions ==="
    node --version 2>/dev/null || echo "Node.js not installed"
    npm --version 2>/dev/null || echo "npm not installed"
    python3 --version 2>/dev/null || echo "Python 3 not installed"
    git --version 2>/dev/null || echo "Git not installed"
    
    log_info "\n=== Project Structure ==="
    ls -la | head -20
    
    log_info "\n=== Common Issues & Solutions ==="
    echo "1. npm ERR! → Try: npm cache clean --force && npm install"
    echo "2. Python venv activation issues → Check: source .venv/bin/activate"
    echo "3. Permission denied → Try: chmod +x <script-name>"
    echo "4. .env missing → Copy: cp .env.example .env"
    echo "5. Port already in use → Kill process: lsof -i :<port>"
}

################################################################################
# MAIN MENU
################################################################################
show_menu() {
    cat << EOF

${BLUE}╔════════════════════════════════════════════╗${NC}
${BLUE}║   Setup Guide Expert - Main Menu          ║${NC}
${BLUE}╚════════════════════════════════════════════╝${NC}

1) ${GREEN}Analyze${NC}      - Analyze project structure & dependencies
2) ${GREEN}Check Deps${NC}    - Check system prerequisites
3) ${GREEN}Setup${NC}        - Run full setup (Node + Python)
4) ${GREEN}Verify${NC}       - Verify setup completed successfully
5) ${GREEN}Troubleshoot${NC} - Run diagnostics & common fixes
6) ${RED}Exit${NC}        - Exit this script

Select an option (1-6):
EOF
}

################################################################################
# MAIN EXECUTION
################################################################################
main() {
    log_info "Setup Guide Expert initialized"
    
    # If action provided as argument, run it directly
    if [ -n "$1" ]; then
        case "$1" in
            analyze)
                analyze_project
                ;;
            check)
                check_dependencies
                ;;
            setup)
                setup_nodejs_project 2>/dev/null || true
                setup_python_project 2>/dev/null || true
                setup_env_files
                ;;
            verify)
                verify_setup
                ;;
            troubleshoot)
                troubleshoot
                ;;
            *)
                log_error "Unknown action: $1"
                exit 1
                ;;
        esac
    else
        # Interactive menu
        while true; do
            show_menu
            read -p "Your choice: " choice
            
            case $choice in
                1)
                    echo ""
                    analyze_project
                    echo ""
                    ;;
                2)
                    echo ""
                    check_dependencies
                    echo ""
                    ;;
                3)
                    echo ""
                    setup_nodejs_project 2>/dev/null || true
                    setup_python_project 2>/dev/null || true
                    setup_env_files
                    echo ""
                    ;;
                4)
                    echo ""
                    verify_setup
                    echo ""
                    ;;
                5)
                    echo ""
                    troubleshoot
                    echo ""
                    ;;
                6)
                    log_success "Exiting Setup Guide Expert"
                    exit 0
                    ;;
                *)
                    log_error "Invalid choice. Please select 1-6."
                    ;;
            esac
        done
    fi
}

# Run main function
main "$@"
