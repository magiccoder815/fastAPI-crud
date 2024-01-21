# Contributing to FastCRUD

Thank you for your interest in contributing to FastCRUD! This guide is meant to make it easy for you to get started.

## Setting Up Your Development Environment

### Cloning the Repository
Start by forking and cloning the FastCRUD repository:

```sh
git clone https://github.com/YOUR-GITHUB-USERNAME/fastcrud.git
```

### Using Poetry for Dependency Management
FastCRUD uses Poetry for managing dependencies. If you don't have Poetry installed, follow the instructions on the [official Poetry website](https://python-poetry.org/docs/).

Once Poetry is installed, navigate to the cloned repository and install the dependencies:
```sh
cd fastcrud
poetry install
```

### Activating the Virtual Environment
Poetry creates a virtual environment for your project. Activate it using:

```sh
poetry shell
```

## Making Contributions

### Coding Standards
- Follow PEP 8 guidelines.
- Write meaningful tests for new features or bug fixes.

### Testing with Pytest
FastCRUD uses pytest for testing. Run tests using:
```sh
poetry run pytest
```

### Linting
Use mypy for type checking:
```sh
mypy fastcrud
```

Use ruff for style:
```sh
ruff check --fix
ruff format
```

Ensure your code passes linting before submitting.

## Submitting Your Contributions

### Creating a Pull Request
After making your changes:

- Push your changes to your fork.
- Open a pull request with a clear description of your changes.
- Update the README.md if necessary.


### Code Reviews
- Address any feedback from code reviews.
- Once approved, your contributions will be merged into the main branch.

##Code of Conduct
Please adhere to our Code of Conduct to maintain a welcoming and inclusive environment.

Thank you for contributing to FastCRUD!
