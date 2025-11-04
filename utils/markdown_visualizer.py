"""
Markdown visualization and PDF export utilities.
Uses Grip for GitHub-flavored markdown preview and optional PDF export.
"""
import os
import sys
import logging
import webbrowser
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MarkdownVisualizer:
    """
    Handles markdown preview and PDF export for workflow guides.
    Uses Grip for GitHub-flavored rendering and WeasyPrint for PDF conversion.
    """

    def __init__(self, host: str = 'localhost', port: int = 6419):
        """
        Initialize markdown visualizer.

        Args:
            host: Host address for preview server
            port: Port for preview server
        """
        self.host = host
        self.port = port
        logger.info(f"[VISUALIZER] Initialized with {host}:{port}")

    def preview_in_browser(self, md_file_path: str, cleanup_html: bool = True) -> bool:
        """
        Open markdown file in browser with GitHub-flavored rendering.
        Generates HTML using Grip and opens it in browser.

        Args:
            md_file_path: Path to markdown file
            cleanup_html: If True, removes temporary HTML file after opening

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[VISUALIZER] Starting browser preview for: {md_file_path}")

        try:
            # Check if file exists
            if not os.path.exists(md_file_path):
                logger.error(f"[VISUALIZER] File not found: {md_file_path}")
                return False

            # Import grip (lazy import to avoid startup cost if not used)
            try:
                import grip
            except ImportError:
                logger.error("[VISUALIZER] Grip not installed. Install with: pip install grip")
                print("\n[ERROR] Grip library not installed!")
                print("Install with: pip install grip")
                return False

            # Get absolute path
            md_path = Path(md_file_path).resolve()
            html_path = md_path.parent / f"{md_path.stem}_preview.html"

            print(f"\n[VISUALIZER] Generating HTML preview...")
            print(f"[VISUALIZER] File: {md_path.name}")

            # Generate HTML with GitHub styling
            logger.info(f"[VISUALIZER] Generating HTML: {html_path}")
            grip.export(path=str(md_path), out_filename=str(html_path))

            # Open HTML in browser
            html_url = html_path.as_uri()
            webbrowser.open(html_url)

            print(f"[VISUALIZER] Preview opened in browser")
            logger.info(f"[VISUALIZER] Opened in browser: {html_url}")

            # Note: We keep the HTML file for now (don't cleanup immediately)
            # User might want to keep it open while using PDF export
            if not cleanup_html:
                print(f"[VISUALIZER] Preview HTML saved: {html_path}")

            return True

        except Exception as e:
            logger.error(f"[VISUALIZER] Preview failed: {str(e)}", exc_info=True)
            print(f"\n[ERROR] Failed to generate preview: {str(e)}")
            return False

    def export_to_pdf(self, md_file_path: str, output_pdf_path: Optional[str] = None, use_browser_fallback: bool = True) -> Optional[str]:
        """
        Export markdown file to PDF.
        Attempts to use WeasyPrint, falls back to browser print instructions on Windows.

        Args:
            md_file_path: Path to markdown file
            output_pdf_path: Optional output PDF path (defaults to same name as md)
            use_browser_fallback: If True, provides browser print instructions on WeasyPrint failure

        Returns:
            Path to generated PDF if successful, HTML path for browser printing, or None
        """
        logger.info(f"[VISUALIZER] Starting PDF export for: {md_file_path}")

        try:
            # Check if file exists
            if not os.path.exists(md_file_path):
                logger.error(f"[VISUALIZER] File not found: {md_file_path}")
                return None

            # Import grip (required)
            try:
                import grip
            except ImportError:
                logger.error("[VISUALIZER] Grip not installed. Install with: pip install grip")
                print("\n[ERROR] Grip library not installed!")
                print("Install with: pip install grip")
                return None

            # Get paths
            md_path = Path(md_file_path).resolve()

            if output_pdf_path is None:
                output_pdf_path = str(md_path.parent / f"{md_path.stem}.pdf")

            output_html_path = str(md_path.parent / f"{md_path.stem}_preview.html")

            print(f"\n[VISUALIZER] Exporting to PDF...")
            print(f"[VISUALIZER] Source: {md_path.name}")

            # Step 1: Export to HTML with GitHub styling
            logger.info(f"[VISUALIZER] Generating HTML: {output_html_path}")
            grip.export(path=str(md_path), out_filename=output_html_path)
            print(f"[VISUALIZER] HTML generated: {Path(output_html_path).name}")

            # Step 2: Try WeasyPrint for PDF conversion
            try:
                from weasyprint import HTML as WeasyHTML

                logger.info(f"[VISUALIZER] Converting to PDF with WeasyPrint: {output_pdf_path}")
                WeasyHTML(output_html_path).write_pdf(output_pdf_path)

                # Clean up temporary HTML file
                try:
                    os.remove(output_html_path)
                    logger.debug(f"[VISUALIZER] Cleaned up temporary HTML: {output_html_path}")
                except Exception as cleanup_error:
                    logger.warning(f"[VISUALIZER] Could not remove temp HTML: {str(cleanup_error)}")

                print(f"[SUCCESS] PDF created: {output_pdf_path}\n")
                logger.info(f"[VISUALIZER] PDF export successful: {output_pdf_path}")

                return output_pdf_path

            except (ImportError, OSError) as pdf_error:
                # WeasyPrint not available or missing dependencies (common on Windows)
                logger.warning(f"[VISUALIZER] WeasyPrint failed: {str(pdf_error)}")

                if use_browser_fallback:
                    # Open HTML in browser and provide print instructions
                    print(f"\n[INFO] WeasyPrint not available (requires system dependencies)")
                    print(f"[INFO] Opening HTML in browser for manual PDF export...\n")

                    html_url = Path(output_html_path).as_uri()
                    webbrowser.open(html_url)

                    print(f"[INSTRUCTIONS] To export as PDF:")
                    print(f"  1. Browser window should now be open")
                    print(f"  2. Press Ctrl+P (or Cmd+P on Mac)")
                    print(f"  3. Select 'Save as PDF' as printer")
                    print(f"  4. Click 'Save'")
                    print(f"\n[INFO] HTML file saved: {output_html_path}\n")

                    logger.info(f"[VISUALIZER] Browser fallback used, HTML saved: {output_html_path}")
                    return output_html_path  # Return HTML path instead of PDF
                else:
                    print(f"\n[ERROR] PDF export failed: {str(pdf_error)}")
                    print(f"[INFO] Install WeasyPrint system dependencies:")
                    print(f"  Windows: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows")
                    print(f"  Or use browser print: Open the HTML file and press Ctrl+P\n")
                    return None

        except Exception as e:
            logger.error(f"[VISUALIZER] PDF export failed: {str(e)}", exc_info=True)
            print(f"\n[ERROR] Failed to export PDF: {str(e)}")
            return None

    def visualize_guide(self, guide_path: str, auto_pdf: bool = False) -> dict:
        """
        Interactive guide visualization with optional PDF export.

        Args:
            guide_path: Path to workflow guide markdown file
            auto_pdf: If True, automatically export to PDF without asking

        Returns:
            Dictionary with visualization results
        """
        logger.info(f"[VISUALIZER] Starting guide visualization: {guide_path}")

        result = {
            'success': False,
            'previewed': False,
            'pdf_exported': False,
            'pdf_path': None,
            'message': ''
        }

        try:
            # Check if file exists
            if not os.path.exists(guide_path):
                result['message'] = f"File not found: {guide_path}"
                logger.error(f"[VISUALIZER] {result['message']}")
                return result

            # Ask user if they want to preview
            print(f"\n[OPTIONAL] Visualize workflow guide in browser? (y/n): ", end='')
            preview_response = input().strip().lower()

            if preview_response == 'y':
                # Generate HTML and open in browser
                success = self.preview_in_browser(guide_path, cleanup_html=False)
                result['previewed'] = success

            # Ask user if they want PDF export
            if auto_pdf:
                export_response = 'y'
            else:
                print(f"\n[OPTIONAL] Export workflow guide to PDF? (y/n): ", end='')
                export_response = input().strip().lower()

            if export_response == 'y':
                pdf_path = self.export_to_pdf(guide_path)
                if pdf_path:
                    result['pdf_exported'] = True
                    result['pdf_path'] = pdf_path
                    result['success'] = True
                    if pdf_path.endswith('.pdf'):
                        result['message'] = f"PDF exported: {pdf_path}"
                    else:
                        result['message'] = f"HTML ready for browser print: {pdf_path}"
                else:
                    result['message'] = "PDF export failed"
            else:
                result['success'] = result['previewed']
                result['message'] = "Visualization completed"

            return result

        except Exception as e:
            logger.error(f"[VISUALIZER] Visualization failed: {str(e)}", exc_info=True)
            result['message'] = f"Visualization failed: {str(e)}"
            return result


def preview_markdown_cli(md_file_path: str, export_pdf: bool = False):
    """
    CLI function for previewing markdown files.

    Args:
        md_file_path: Path to markdown file
        export_pdf: If True, exports to PDF
    """
    visualizer = MarkdownVisualizer()

    if export_pdf:
        visualizer.export_to_pdf(md_file_path)
    else:
        visualizer.preview_in_browser(md_file_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python markdown_visualizer.py <markdown_file> [--pdf]")
        print("Example: python markdown_visualizer.py WORKFLOW_GUIDE.md")
        print("Example: python markdown_visualizer.py WORKFLOW_GUIDE.md --pdf")
        sys.exit(1)

    md_file = sys.argv[1]
    export_pdf = "--pdf" in sys.argv or "-p" in sys.argv

    preview_markdown_cli(md_file, export_pdf)
