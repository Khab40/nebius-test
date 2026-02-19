# Nebius Test Project

A test project for Nebius cloud platform integration and development using Python.

## Setup

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Virtual environment (venv or similar)
- Nebius Cloud account

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nebius-test
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

5. Update `.env` with your Nebius credentials:
```
NEBIUS_API_KEY=<your-api-key>
NEBIUS_API_SECRET=<your-api-secret>
NEBIUS_ACCOUNT_ID=<your-account-id>
```

### Running the Project

```bash
python main.py
```

## Configuration

All configuration is managed through environment variables in the `.env` file. See `.env` for available options.

## Development

```bash
python main.py --debug
```

## Contributing

Please follow the project's contribution guidelines.

## License

MIT
