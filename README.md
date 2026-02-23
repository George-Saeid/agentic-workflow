# Agentic Workflow

A 3-layer architecture system that separates LLM orchestration from deterministic execution, maximizing reliability and maintainability.

## Architecture Overview

This project implements a three-layer architecture:

### Layer 1: Directives (What to do)
- Standard Operating Procedures written in Markdown
- Located in `directives/`
- Define goals, inputs, tools/scripts to use, outputs, and edge cases
- Natural language instructions that guide the AI orchestrator

### Layer 2: Orchestration (Decision making)
- AI agent that reads directives and makes intelligent routing decisions
- Calls execution tools in the right order
- Handles errors and asks for clarification when needed
- Updates directives with learnings over time

### Layer 3: Execution (Doing the work)
- Deterministic Python scripts in `execution/`
- Handles API calls, data processing, file operations, and database interactions
- Reliable, testable, and fast
- No LLM uncertainty in this layer

## Directory Structure

```
.
├── directives/          # Markdown SOPs (instruction set)
├── execution/           # Python scripts (deterministic tools)
├── .tmp/                # Intermediate files (never commit)
├── .env                 # Environment variables and API keys
├── .env.example         # Template for environment variables
├── credentials.json     # Google OAuth credentials (gitignored)
├── token.json           # Google OAuth token (gitignored)
├── AGENTS.md            # Architecture documentation
└── README.md            # This file
```

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- Git
- Access to required APIs (Google, OpenAI, etc.)

### 2. Installation

```bash
# Clone or initialize the repository
git init

# Install Python dependencies
pip install -r requirements.txt

# Copy the environment template
copy .env.example .env    # Windows
# cp .env.example .env    # Linux/Mac
```

### 3. Configuration

Edit `.env` and add your API keys and credentials:
- Google API credentials (for Sheets, Slides, etc.)
- OpenAI or Anthropic API keys (if using)
- Any other required API credentials

### 4. Google OAuth Setup (if needed)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable required APIs (Sheets, Slides, Drive, etc.)
4. Create OAuth 2.0 credentials
5. Download credentials and save as `credentials.json` in the project root

See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for detailed setup instructions.

## Usage

### Google Sheets Structure Analyzer

Analyze the complete structure of any Google Sheet:

```powershell
py execution\analyze_sheet_structure.py "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
```

**What it extracts:**
- All sheets/tabs in the spreadsheet
- Column headers and row headers
- Data types for each column (number, text, date, URL, email, boolean)
- Row and column counts
- Sample data from each sheet
- Grid properties and metadata

**Output:** JSON file saved to `.tmp/sheet_analysis_{spreadsheet_id}.json`

**First time setup:** See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for Google API authentication.

### Creating a New Directive

1. Create a new Markdown file in `directives/`
2. Follow this template:

```markdown
# [Task Name]

## Goal
What this task accomplishes

## Inputs
- Input 1: Description
- Input 2: Description

## Tools/Scripts
- `execution/script_name.py`: What it does

## Outputs
- Output 1: Description
- Output 2: Description

## Edge Cases
- Edge case 1: How to handle it
- Edge case 2: How to handle it

## Notes
Additional context or considerations
```

### Creating a New Execution Script

1. Create a new Python file in `execution/`
2. Make it deterministic and testable
3. Use environment variables from `.env`
4. Return clear success/failure status
5. Handle errors gracefully

Example structure:
```python
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    # Your deterministic logic here
    pass

if __name__ == "__main__":
    main()
```

### Running the System

The AI orchestrator will:
1. Read the relevant directive
2. Determine which execution scripts to run
3. Execute them in the correct order
4. Handle errors and update directives as needed

## Key Principles

### Deliverables vs Intermediates
- **Deliverables**: Cloud-based outputs (Google Sheets, Slides, etc.)
- **Intermediates**: Temporary files in `.tmp/` (can be deleted and regenerated)

### Self-Annealing
When errors occur:
1. Read the error message and stack trace
2. Fix the script and test again
3. Update the directive with learnings
4. System becomes stronger over time

### Update Directives as You Learn
Directives are living documents. When you discover:
- API constraints or rate limits
- Better approaches
- Common errors
- Timing expectations

Update the directive so future runs benefit from this knowledge.

## Best Practices

1. **Check for tools first**: Before creating a new script, check if one already exists
2. **Keep execution deterministic**: No LLM calls in execution scripts
3. **Use intermediate files wisely**: Everything in `.tmp/` should be regenerable
4. **Document learnings**: Update directives when you discover edge cases
5. **Test scripts independently**: Each script in `execution/` should be testable on its own

## Contributing

When adding new functionality:
1. Create or update the directive first
2. Write or modify the execution script
3. Test thoroughly
4. Update documentation

## License

[Add your license here]
