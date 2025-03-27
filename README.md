# HyperBlend

HyperBlend is a powerful tool for analyzing natural compounds, their sources, and biological targets. It provides an interactive graph-based interface for exploring relationships between compounds, natural sources (plants, fungi, etc.), and biological targets.

## Features

- Interactive force-directed graph visualization
- Search across multiple scientific databases
- Real-time data retrieval and updates
- Detailed information panels
- Subgraph visualization for related entities
- Support for various data sources:
  - PubChem
  - ChemSpider
  - ChEMBL
  - ChEBI
  - DrugBank
  - UniProt
  - RCSB
  - STITCH
  - KNApSAcK
  - NPASS
  - TCMSP
  - UNPD
  - LOTUS
  - COCONUT

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/hyperblend.git
cd hyperblend
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up Neo4j:

- Install Neo4j Community Edition
- Create a new database
- Update the connection details in .env

## Usage

1. Start the Flask development server:

```bash
cd /Users/Adam/HyperBlend && python -m hyperblend.app.web.app
```

2. Open your browser and navigate to `http://localhost:5000`

3. Use the search bar to find compounds, sources, or targets

4. Click on nodes in the graph to view detailed information

5. Use the sidebar to explore related entities

## Project Structure

```
hyperblend/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Core functionality
│   ├── db/           # Database models and connections
│   ├── models/       # Pydantic models
│   ├── services/     # Business logic
│   ├── utils/        # Utility functions
│   └── web/          # Web interface
│       ├── static/   # Static files (JS, CSS)
│       └── templates/# HTML templates
├── config/           # Configuration files
├── tests/            # Test files
├── .env              # Environment variables
├── .env.example      # Example environment variables
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Development

### Running Tests

```bash
pytest
```

### Code Style

This project follows:

- SOLID principles
- Google Style Guide
- Modern programming patterns
- Clean code rules

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Neo4j for the graph database
- D3.js for the graph visualization
- Flask for the web framework
- Pydantic for data validation
- All the scientific databases and their APIs
