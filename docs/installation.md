# Installation

## Requirements

- Python 3.10 or higher
- pip (Python package installer)

## Installing from PyPI

The easiest way to install SSMD is using pip:

```bash
pip install ssmd
```

This will install the latest stable release from PyPI.

## Installing from Source

If you want to install from source or contribute to development:

1. Clone the repository:

```bash
git clone https://github.com/buchwandler/ssmd.git
cd ssmd
```

2. Install in development mode:

```bash
pip install -e .
```

This will install SSMD in editable mode, so any changes you make to the source code will
be immediately reflected.

## Development Installation

For development with all testing and documentation tools:

```bash
# Clone and enter directory
git clone https://github.com/buchwandler/ssmd.git
cd ssmd

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

This installs additional dependencies for:

- Testing (pytest, pytest-cov)
- Type checking (mypy)
- Linting and formatting (ruff)
- Documentation building (Sphinx)

The optional `ssml-maker` integration tests are installed separately with
`pip install -e ".[integration]"`.

## Verifying Installation

To verify that SSMD is installed correctly:

```python
import ssmd

# Check version
print(ssmd.__version__)

# Quick test
result = ssmd.to_ssml("Hello *world*!")
print(result)
# Should output: <speak>Hello <emphasis>world</emphasis>!</speak>
```

## Dependencies

SSMD has minimal runtime dependencies:

- `phrasplit>=0.3.4` - sentence detection, model resolution, and splitting; the 0.2.x
  line does not satisfy SSMD's paragraph and markup round-trip contract
- `pyyaml` - YAML front matter parsing

Optional dependencies for development:

- **Testing**: pytest, pytest-cov
- **Type checking**: mypy
- **Linting**: ruff
- **Documentation**: Sphinx, sphinx-rtd-theme
- **Build**: setuptools-scm, build

## Building Release Artifacts

Release versions are derived by `setuptools-scm` from Git tag context. A source snapshot
without `.git` metadata, or a build that cannot install the configured build
requirements, may produce a fallback version such as `0.0.0`; that output is not a
release artifact. Release builds must run from the exact `v<version>` tag and pass the
repository's artifact filename and metadata check before publication.

## Upgrading

To upgrade to the latest version:

```bash
pip install --upgrade ssmd
```

## Uninstalling

To remove SSMD from your system:

```bash
pip uninstall ssmd
```
