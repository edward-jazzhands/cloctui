# Install the package
install:
	uv sync

# Run the demo with defined entry command
run:
	uv run cloctui

# Run the demo in dev mode
run-dev:
	uv run textual run --dev cloctui.main:ClocTUI

# Run the console
console:
	uv run textual console -x EVENT -x SYSTEM

# Runs ruff, exits with 0 if no issues are found
lint:
	uv run ruff check src || (echo "Ruff found issues. Please address them." && exit 1)

# Runs mypy, exits with 0 if no issues are found
typecheck:
	uv run mypy src || (echo "Mypy found issues. Please address them." && exit 1)

# Runs black
format:
	uv run black src

# Runs ruff, mypy, and black
all-checks: lint typecheck format
	echo "All pre-commit checks passed. You're good to publish."	

# Build the package, run clean first
build: clean
	@echo "Building the package..."
	uv build
	
# Publish the package, run build first
publish: build
	@echo "Publishing the package..."
	uv publish

# Remove the build and dist directories
clean:
	rm -rf build dist
	find . -name "*.pyc" -delete

# Remove the virtual environment and lock file
del-env:
	rm -rf .venv
	rm -rf uv.lock

reset: clean del-env install
	@echo "Resetting the environment..."
#-------------------------------------------------------------------------------