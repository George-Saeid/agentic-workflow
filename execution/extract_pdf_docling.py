"""
PDF Data Extractor using IBM Docling
Extracts text, tables, images, and document structure from PDF files.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("Error: docling library not installed")
    print("Please install it with: pip install docling")
    sys.exit(1)


def extract_pdf(
    pdf_path: str,
    output_format: str = "json",
    extract_images: bool = True,
    extract_tables: bool = True
) -> Dict[str, Any]:
    """
    Extract data from PDF using Docling.
    
    Args:
        pdf_path: Path to the PDF file
        output_format: Output format - "markdown", "json", "text", or "all"
        extract_images: Whether to extract and save images
        extract_tables: Whether to extract tables separately
        
    Returns:
        Dictionary with status, message, and output file paths
    """
    try:
        # Validate inputs
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            return {
                "status": "error",
                "message": f"PDF file not found: {pdf_path}"
            }
        
        if not pdf_file.suffix.lower() == '.pdf':
            return {
                "status": "error",
                "message": f"Invalid file type: {pdf_file.suffix}. Expected .pdf"
            }
        
        # Setup output directory
        project_root = Path(__file__).parent.parent
        tmp_dir = project_root / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        
        # Generate output filename base
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = pdf_file.stem
        output_base = f"pdf_extract_{file_stem}_{timestamp}"
        
        # Setup image directory if needed
        image_dir = None
        if extract_images:
            image_dir = tmp_dir / f"pdf_images_{file_stem}_{timestamp}"
            image_dir.mkdir(exist_ok=True)
        
        print(f"Processing PDF: {pdf_file.name}")
        print(f"File size: {pdf_file.stat().st_size:,} bytes")
        
        # Initialize converter with default options
        # Docling automatically handles OCR and table extraction
        converter = DocumentConverter()
        
        # Convert the document
        print("Extracting content with Docling...")
        result = converter.convert(str(pdf_file))
        
        # Extract metadata
        metadata = {
            "filename": pdf_file.name,
            "file_path": str(pdf_file.absolute()),
            "file_size_bytes": pdf_file.stat().st_size,
            "extraction_date": datetime.now().isoformat(),
            "page_count": len(result.pages) if hasattr(result, 'pages') else None,
            "output_format": output_format,
        }
        
        # Build structured output
        output_data = {
            "metadata": metadata,
            "document_structure": {},
            "pages": [],
            "tables": [],
            "images": []
        }
        
        # Extract document content
        if hasattr(result, 'document'):
            doc = result.document
            
            # Get full text
            full_text = doc.export_to_text() if hasattr(doc, 'export_to_text') else str(doc)
            
            # Get structured content
            if hasattr(doc, 'sections'):
                sections = []
                for section in doc.sections:
                    section_data = {
                        "heading": section.heading if hasattr(section, 'heading') else None,
                        "level": section.level if hasattr(section, 'level') else None,
                        "text": section.text if hasattr(section, 'text') else str(section)
                    }
                    sections.append(section_data)
                output_data["document_structure"]["sections"] = sections
            
            # Extract tables if available
            if extract_tables and hasattr(doc, 'tables'):
                for idx, table in enumerate(doc.tables, 1):
                    table_data = {
                        "table_index": idx,
                        "data": table.export_to_dict() if hasattr(table, 'export_to_dict') else str(table)
                    }
                    output_data["tables"].append(table_data)
            
            # Extract images if available
            if extract_images and hasattr(doc, 'pictures') and image_dir:
                for idx, picture in enumerate(doc.pictures, 1):
                    image_filename = f"image_{idx:03d}.png"
                    image_path = image_dir / image_filename
                    
                    # Save image if possible
                    try:
                        if hasattr(picture, 'get_image'):
                            img = picture.get_image()
                            img.save(str(image_path))
                        elif hasattr(picture, 'image_bytes'):
                            image_path.write_bytes(picture.image_bytes)
                        
                        image_data = {
                            "image_index": idx,
                            "path": str(image_path.relative_to(project_root)),
                            "filename": image_filename
                        }
                        output_data["images"].append(image_data)
                    except Exception as img_error:
                        print(f"Warning: Could not extract image {idx}: {img_error}")
        
        # Get full text in different formats
        full_text = result.document.export_to_text() if hasattr(result, 'document') else str(result)
        markdown_text = result.document.export_to_markdown() if hasattr(result.document, 'export_to_markdown') else full_text
        
        # Save outputs based on format requested
        output_files = {}
        
        # Always save JSON
        if output_format in ["json", "all"]:
            json_path = tmp_dir / f"{output_base}.json"
            output_data["full_text"] = full_text
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            output_files["json"] = str(json_path)
            print(f"[OK] Saved JSON: {json_path.name}")
        
        # Save Markdown if requested
        if output_format in ["markdown", "all"]:
            md_path = tmp_dir / f"{output_base}.md"
            md_path.write_text(markdown_text, encoding='utf-8')
            output_files["markdown"] = str(md_path)
            print(f"[OK] Saved Markdown: {md_path.name}")
        
        # Save plain text if requested
        if output_format in ["text", "all"]:
            txt_path = tmp_dir / f"{output_base}.txt"
            txt_path.write_text(full_text, encoding='utf-8')
            output_files["text"] = str(txt_path)
            print(f"[OK] Saved Text: {txt_path.name}")
        
        # Prepare summary
        summary = {
            "status": "success",
            "message": f"Successfully extracted data from {pdf_file.name}",
            "output_files": output_files,
            "stats": {
                "pages": metadata.get("page_count", "unknown"),
                "tables": len(output_data["tables"]),
                "images": len(output_data["images"]),
                "text_length": len(full_text),
            }
        }
        
        if image_dir and output_data["images"]:
            summary["image_directory"] = str(image_dir.relative_to(project_root))
        
        return summary
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to extract PDF: {str(e)}",
            "error_type": type(e).__name__
        }


def main():
    """Main entry point for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract data from PDF using Docling")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "text", "all"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image extraction"
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Skip table extraction"
    )
    
    args = parser.parse_args()
    
    result = extract_pdf(
        pdf_path=args.pdf_path,
        output_format=args.format,
        extract_images=not args.no_images,
        extract_tables=not args.no_tables
    )
    
    print(f"\n{'='*60}")
    print(f"Status: {result['status'].upper()}")
    print(f"{'='*60}")
    print(f"Message: {result['message']}")
    
    if result["status"] == "success":
        print(f"\nOutput Files:")
        for format_type, file_path in result["output_files"].items():
            print(f"  {format_type.capitalize()}: {file_path}")
        
        print(f"\nStatistics:")
        for key, value in result["stats"].items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        if "image_directory" in result:
            print(f"\nImages saved to: {result['image_directory']}")
    else:
        print(f"Error: {result.get('error_type', 'Unknown')}")
    
    # Exit with appropriate code
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
