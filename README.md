# HyperBlend

A chemical compound analysis and visualization platform that integrates data from PubChem and ChEMBL.

## Features

- Compound management with data from PubChem and ChEMBL
- Source tracking (plants, fungi, etc.)
- Biological target analysis
- Graph-based relationship visualization
- REST API for data access and management

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/hyperblend.git
cd hyperblend
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Development Setup

1. Set up the database:

```bash
# The database will be automatically created on first run
```

2. Run the development server:

```bash
uvicorn hyperblend.web.api:app --reload
```

3. Access the API documentation:

- OpenAPI UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=hyperblend tests/
```

## Project Structure

```
hyperblend/
├── domain/             # Domain models and business logic
│   ├── models/        # Core domain models
│   └── interfaces/    # Abstract interfaces
├── application/       # Application services
│   └── services/     # Service layer implementations
├── infrastructure/    # Infrastructure implementations
│   ├── database/     # Database configuration
│   └── repositories/ # Repository implementations
├── web/              # Web interface
│   └── api/         # REST API endpoints
└── config/           # Configuration settings
```

## API Endpoints

- `/compounds`: Compound management
- `/sources`: Source management
- `/targets`: Biological target management

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
