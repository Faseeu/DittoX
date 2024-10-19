### dittoX 🚀

[![License](https://img.shields.io/github/license/faseeu/dittox)](LICENSE)

**dittoX** - *the advanced twin of simplest self-building coding agent for FastAPI*.


![Image Description](ditto.png)

**dittoX** is a fork of the original [Ditto](https://github.com/yoheinakajima/ditto) project, adapted to work with FastAPI instead of Flask. This tool allows you to generate a multi-file FastAPI application from simple natural language descriptions using a no-code interface. By leveraging a simple LLM loop with a few tools, dittoX automates the coding process, (occasionally) turning your ideas into functional web applications (or at least trying and getting close).

## Features 🌟

- **Simple Natural Language Input**: Just describe the application you want to build in plain English.
- **Automated Code Generation**: Generates routes, templates, and static files based on your description.
- **Self-Building Agent**: Automatically plans and constructs the application without the need for manual coding.
- **Modular Structure**: Organizes code into a clean, modular structure with separate directories for templates, static files, and routes.
- **FastAPI Integration**: Utilizes FastAPI for high-performance, async web applications.
- **Updated Dependencies**: Uses the latest versions of FastAPI and related libraries.
- **Enhanced Error Handling**: Improved error handling and logging for better debugging.
- **API Documentation**: Automatically generates API documentation using FastAPI's built-in support.

## Getting Started 🚀

### Prerequisites

- Python 3.7 or higher
- `pip` package manager

### Installation

```bash
git clone https://github.com/yourusername/dittox.git
cd dittox
```

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

### Setting the `OPENAI_API_KEY`

To use dittoX, you'll need to set the `OPENAI_API_KEY` in your environment. Here are two options for doing that:

#### Option 1: Temporary Setup in Terminal

For macOS/Linux:

```bash
export OPENAI_API_KEY=your-openai-api-key
```

For Windows (Command Prompt):

```cmd
set OPENAI_API_KEY=your-openai-api-key
```

For Windows (PowerShell):

```powershell
$env:OPENAI_API_KEY="your-openai-api-key"
```

Run the application:

```bash
python main.py
```

#### Option 2: Persistent Setup using a `.env` File (Recommended)

```bash
pip install python-dotenv
```

```bash
OPENAI_API_KEY=your-openai-api-key
```

```bash
python main.py
```

### Usage

```bash
python main.py
```

```bash
http://localhost:8000
```

```bash
python main.py
```

## Contribution 🤝

This is a fork of the original Ditto project, and contributions are welcome! If you have any improvements or new features, feel free to submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
