# Workflow Guide Visualization

Flow-Planner includes a built-in visualization system that allows you to preview workflow guides in your browser and export them to PDF format.

## Features

### 1. Browser Preview
- Opens markdown guides in your default browser
- GitHub-flavored markdown rendering (via Grip)
- View screenshots inline with guide text
- Perfect for reviewing guides before sharing

### 2. PDF Export
- Convert workflow guides to professional PDF documents
- Preserves formatting, screenshots, and styling
- Ideal for documentation and sharing with non-technical users
- Uses WeasyPrint for high-quality PDF generation

## Usage

### Interactive Mode

After workflow capture completes, you'll be prompted:

```
[OPTIONAL] Visualize workflow guide in browser? (y/n):
```

**If you select 'y':**
1. The guide opens in your default browser
2. You'll then be prompted:
   ```
   [OPTIONAL] Export workflow guide to PDF? (y/n):
   ```
3. If you select 'y', a PDF will be generated in the same directory as the guide

**If you select 'n':**
- Visualization is skipped
- Guide remains in markdown format in the output directory

### Command Line Usage

You can also use the visualizer standalone:

```bash
# Preview a guide in browser
python utils/markdown_visualizer.py output/run1/WORKFLOW_GUIDE.md

# Export directly to PDF
python utils/markdown_visualizer.py output/run1/WORKFLOW_GUIDE.md --pdf
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Enable/disable visualization feature
ENABLE_VISUALIZATION=true

# Visualization server settings (for Grip preview)
VISUALIZATION_HOST=localhost
VISUALIZATION_PORT=6419

# Auto-export to PDF without prompting
AUTO_EXPORT_PDF=false
```

### Config Options

- **ENABLE_VISUALIZATION**: Set to `false` to completely skip visualization prompts
- **VISUALIZATION_HOST**: Host for Grip preview server (default: localhost)
- **VISUALIZATION_PORT**: Port for Grip preview server (default: 6419)
- **AUTO_EXPORT_PDF**: Set to `true` to automatically export PDFs without prompting

## Dependencies

The visualization feature requires:

```bash
pip install grip        # GitHub-flavored markdown rendering
pip install weasyprint  # PDF export
```

These are already included in `requirements.txt`.

## How It Works

### Browser Preview
1. Uses **Grip** to render markdown with GitHub styling
2. Opens `file://` URL in your default browser
3. Screenshots are loaded from the workflow output directory
4. No server needed - just opens the file directly

### PDF Export
1. Grip converts markdown to styled HTML
2. **WeasyPrint** renders HTML to PDF
3. Preserves all formatting, images, and layout
4. Temporary HTML file is cleaned up automatically

## Tips

### For Best Results

1. **Review before exporting**: Always preview in browser first to check formatting
2. **Check screenshots**: Ensure all screenshots are properly embedded
3. **PDF file size**: PDFs can be large if many screenshots are included
4. **Refined guides**: If you ran refinement, the refined guide will be used for visualization

### Troubleshooting

**"Grip not installed" error:**
```bash
pip install grip
```

**"WeasyPrint not installed" error:**
```bash
pip install weasyprint
```

**PDF export fails:**
- WeasyPrint requires additional system dependencies on some platforms
- See: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation

**Browser doesn't open:**
- Check that you have a default browser configured
- The markdown file path will be printed - you can open it manually

## Examples

### Example 1: Full Workflow with Visualization

```
[4/4] Generating workflow guide...
[OK] Workflow guide generated: output/youtube_20251104_011121/WORKFLOW_GUIDE.md

[OPTIONAL] Refine workflow with Vision AI? (y/n): y
[5/6] Refining workflow with Vision AI...
[OK] Workflow refined!
  - Refined steps: 4/4
  - Enhanced guide: output/youtube_20251104_011121/REFINED_WORKFLOW_GUIDE.md

[OPTIONAL] Visualize workflow guide in browser? (y/n): y
[6/6] Opening guide in browser...
[OK] Guide opened in default browser

[OPTIONAL] Export workflow guide to PDF? (y/n): y
[INFO] Exporting to PDF...
[OK] PDF exported: output/youtube_20251104_011121/REFINED_WORKFLOW_GUIDE.pdf
```

### Example 2: Skip Visualization

```
[OPTIONAL] Visualize workflow guide in browser? (y/n): n
[INFO] Skipping visualization
```

### Example 3: Standalone PDF Export

```bash
cd output/youtube_20251104_011121
python ../../utils/markdown_visualizer.py WORKFLOW_GUIDE.md --pdf
```

Output:
```
[VISUALIZER] Exporting to PDF...
[VISUALIZER] Source: WORKFLOW_GUIDE.md
[VISUALIZER] Output: WORKFLOW_GUIDE.pdf
[SUCCESS] PDF created: WORKFLOW_GUIDE.pdf
```

## Integration with Refinement

The visualization step is integrated with the refinement workflow:

1. **Original guide**: Generated after step 4 (guide generation)
2. **Refined guide**: Generated after step 5 (refinement) - if enabled
3. **Visualization**: Uses refined guide if available, otherwise uses original

This ensures you're always visualizing the best version of the guide.

## Output Files

After running with visualization enabled, you'll have:

```
output/
  youtube_20251104_011121/
    ├── metadata.json                      # Workflow metadata
    ├── WORKFLOW_GUIDE.md                  # Original guide
    ├── REFINED_WORKFLOW_GUIDE.md          # Refined guide (if enabled)
    ├── REFINED_WORKFLOW_GUIDE.pdf         # PDF export (if selected)
    ├── refinement_metadata.json           # Refinement details (if enabled)
    ├── step_001.png                       # Original screenshots
    ├── step_002.png
    ├── step_003_refined.png               # Refined screenshots (if enabled)
    └── step_004_refined.png
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Workflow Completion                    │
│  (Guide + Optional Refinement Complete)         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│   Visualization Prompt                          │
│   "Visualize guide in browser? (y/n)"           │
└─────┬──────────────────────────────────┬────────┘
      │ yes                                │ no
      ▼                                    ▼
┌──────────────────┐              ┌───────────────┐
│  Open in Browser │              │ Skip & Exit   │
│  (file:// URL)   │              └───────────────┘
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│   PDF Export Prompt                             │
│   "Export to PDF? (y/n)"                        │
└─────┬──────────────────────────────────┬────────┘
      │ yes                                │ no
      ▼                                    ▼
┌──────────────────┐              ┌───────────────┐
│  Grip → HTML     │              │ Complete      │
│  WeasyPrint→PDF  │              └───────────────┘
│  Cleanup & Done  │
└──────────────────┘
```

## Related Documentation

- [REFINEMENT_AGENT.md](REFINEMENT_AGENT.md) - Vision AI screenshot refinement
- [README.md](README.md) - Main project documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture details
