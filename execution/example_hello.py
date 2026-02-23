"""
Example Hello World Script
Demonstrates the basic structure of an execution script.
"""
import os
import sys
from pathlib import Path

def hello(name: str = "World") -> dict:
    """
    Generate a greeting message.
    
    Args:
        name: The name to greet
        
    Returns:
        Dictionary with status and message
    """
    try:
        # Validate input
        if not name or not name.strip():
            name = "World"
        
        # Clean the name (basic sanitization)
        name = name.strip()
        
        # Generate greeting
        greeting = f"Hello, {name}!"
        
        # Save to intermediate file
        tmp_dir = Path(__file__).parent.parent / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        
        output_file = tmp_dir / "greeting.txt"
        output_file.write_text(greeting, encoding="utf-8")
        
        return {
            "status": "success",
            "message": greeting,
            "file": str(output_file)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate greeting: {str(e)}"
        }

def main():
    """Main entry point for command line usage."""
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    result = hello(name)
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    if "file" in result:
        print(f"File: {result['file']}")
    
    # Exit with appropriate code
    sys.exit(0 if result["status"] == "success" else 1)

if __name__ == "__main__":
    main()
