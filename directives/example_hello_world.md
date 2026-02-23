# Example: Hello World Task

> This is a sample directive to demonstrate the structure and workflow.

## Goal
Demonstrate the basic structure of a directive and how it connects to an execution script.

## Inputs
- `name` (string): The name to greet

## Tools/Scripts
- `execution/example_hello.py`: A simple script that generates a greeting message

## Outputs
- Success message withgreeting
- File saved to `.tmp/greeting.txt` (intermediate file)

## Process
1. AI orchestrator reads this directive
2. AI calls `execution/example_hello.py` with the name parameter
3. Script generates greeting and saves to `.tmp/greeting.txt`
4. AI reports success to user

## Edge Cases
- Empty name: Use "World" as default
- Special characters in name: Escape properly

## Notes
This is a minimal example to show the workflow. Real directives will be more complex and may involve multiple scripts, API calls, and data processing steps.
