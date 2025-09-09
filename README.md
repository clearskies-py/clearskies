# clearskies

clearskies is a very opinionated Python framework intended for developing microservices in the cloud via declarative programming principles.  It is mainly intended for backend services and so is designed for RESTful API endpoints, queue listeners, scheduled tasks, and the like.

## Installation

```bash
uv add clear-skies
```

or

```bash
pip install clear-skies
```

or

```bash
pipenv install clear-skies
```

or

```bash
poetry add clear-skies
```

## Development

To set up your development environment with pre-commit hooks:

```bash
# Install uv if not already installed
pip install uv

# Create a virtual environment and install all dependencies (including dev)
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Optionally, run pre-commit on all files
uv run pre-commit run --all-files
```
