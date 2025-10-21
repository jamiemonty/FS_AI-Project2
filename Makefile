# Makefile for AI Stock Trading Backtesting Project
# Created using GPT-4o (ChatGPT)

# Project configuration
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/Scripts/python.exe
PIP = $(VENV_DIR)/Scripts/pip.exe
ACTIVATE = $(VENV_DIR)/Scripts/Activate.ps1

# Default target
.DEFAULT_GOAL := help

# Display help information
help:
	@echo "AI Stock Trading Backtesting Project - Makefile Commands"
	@echo "======================================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Create virtual environment and install dependencies"
	@echo "  make install        - Install required Python packages"
	@echo "  make clean          - Clean up generated files and directories"
	@echo ""
	@echo "Run Commands:"
	@echo "  make run            - Run full analysis (includes optimization, takes 30+ min)"
	@echo "  make quick          - Run quick analysis (uses pre-optimized params, 10-15 min)"
	@echo "  make single YEAR=2024 - Run analysis for single year"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make check          - Check if environment is set up correctly"
	@echo "  make results        - Display latest results summary"
	@echo "  make plots          - Count generated plot files"
	@echo "  make backup         - Create backup of results"
	@echo ""
	@echo "Examples:"
	@echo "  make setup && make quick    # First time setup and quick run"
	@echo "  make single YEAR=2023      # Analyze just 2023"
	@echo "  make clean && make run      # Clean start with full analysis"

# Create virtual environment and install dependencies
setup:
	@echo "Setting up virtual environment..."
	@powershell -Command "python -m venv $(VENV_DIR)"
	@echo "Installing dependencies..."
	@$(PIP) install pandas numpy matplotlib
	@echo "Setup complete! Use 'make run' or 'make quick' to start analysis."

# Install required packages
install:
	@echo "Installing required packages..."
	@$(PIP) install pandas numpy matplotlib
	@echo "Installation complete!"

# Run full analysis with optimization
run: check
	@echo "Starting full analysis with optimization (this may take 30+ minutes)..."
	@$(PYTHON) main.py

# Run quick analysis with pre-optimized parameters
quick: check
	@echo "Starting quick analysis with pre-optimized parameters..."
	@$(PYTHON) -c "from playGround import quick_run; quick_run()"

# Run analysis for single year
single: check
ifndef YEAR
	@echo "Error: Please specify YEAR. Example: make single YEAR=2024"
	@exit 1
endif
	@echo "Running analysis for year $(YEAR)..."
	@$(PYTHON) -c "from playGround import backtest_year; import json; result = backtest_year($(YEAR), 50, 0.30, 30); print(f'Year $(YEAR) Results:'); print(f'Total trades: {result[\"total_trades\"]}'); print(f'Win rate: {result[\"win_rate\"]:.1f}%'); print(f'Compound return: {result[\"compounded_return\"]:.2f}%')"

# Check if environment is properly set up
check:
	@if not exist "$(VENV_DIR)" ( echo "Virtual environment not found. Run 'make setup' first." && exit 1 )
	@if not exist "YahooStockData" ( echo "YahooStockData directory not found. Please ensure stock data is available." && exit 1 )
	@echo "Environment check passed!"

# Display results summary
results:
	@if exist "comprehensive_results.txt" ( \
		echo "=== LATEST RESULTS SUMMARY ===" && \
		powershell -Command "Get-Content comprehensive_results.txt | Select-Object -First 20" && \
		echo "" && \
		echo "Full results available in comprehensive_results.txt" \
	) else ( \
		echo "No results found. Run 'make run' or 'make quick' first." \
	)

# Count generated plot files
plots:
	@echo "Counting generated plot files..."
	@powershell -Command "$$dirs = Get-ChildItem -Directory -Name 'plots_*'; if ($$dirs) { foreach ($$dir in $$dirs) { $$count = (Get-ChildItem $$dir -Filter '*.png' | Measure-Object).Count; Write-Host \"$$dir/: $$count plots\" } } else { Write-Host 'No plot directories found.' }"

# Create backup of results
backup:
	@echo "Creating backup of results..."
	@powershell -Command "$$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'; $$backupDir = \"backup_$$timestamp\"; New-Item -ItemType Directory -Path $$backupDir | Out-Null; Copy-Item '*.csv' $$backupDir -ErrorAction SilentlyContinue; Copy-Item '*.txt' $$backupDir -ErrorAction SilentlyContinue; Copy-Item 'plots_*' $$backupDir -Recurse -ErrorAction SilentlyContinue; Write-Host \"Backup created in $$backupDir\""

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	@powershell -Command "Remove-Item '*_perf.csv' -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item 'comprehensive_results.txt' -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item 'results.txt' -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item 'plots_*' -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item 'backup_*' -Recurse -Force -ErrorAction SilentlyContinue"
	@echo "Cleanup complete!"

# Development commands
dev-install:
	@echo "Installing development dependencies..."
	@$(PIP) install pandas numpy matplotlib jupyter ipykernel
	@echo "Development setup complete!"

# Test environment
test:
	@echo "Testing Python environment..."
	@$(PYTHON) -c "import pandas as pd; import numpy as np; import matplotlib.pyplot as plt; print('All packages imported successfully!')"
	@echo "Environment test passed!"

# Show project status
status:
	@echo "=== PROJECT STATUS ==="
	@echo "Python executable: $(PYTHON)"
	@if exist "$(PYTHON)" ( echo "✓ Python environment: Ready" ) else ( echo "✗ Python environment: Not found" )
	@if exist "YahooStockData" ( echo "✓ Stock data: Available" ) else ( echo "✗ Stock data: Missing" )
	@powershell -Command "$$csvCount = (Get-ChildItem '*_perf.csv' -ErrorAction SilentlyContinue | Measure-Object).Count; Write-Host \"CSV files: $$csvCount\""
	@powershell -Command "$$plotDirs = (Get-ChildItem 'plots_*' -Directory -ErrorAction SilentlyContinue | Measure-Object).Count; Write-Host \"Plot directories: $$plotDirs\""
	@if exist "comprehensive_results.txt" ( echo "✓ Results: Available" ) else ( echo "✗ Results: Not generated" )

# Force targets (don't check for files with same names)
.PHONY: help setup install run quick single check results plots backup clean dev-install test status
