# Coding Rules and Standards

## Critical Rules
1. NO EMOJIS - Use text-based indicators only
2. NO HARDCODING - Use environment variables and configuration
3. COMPREHENSIVE LOGGING - Log all important operations
4. GRACEFUL ERROR HANDLING - All external calls must have try-except
5. NO PARTIAL IMPLEMENTATIONS - Fully implement or document clearly
6. PROPER LOGGING SETUP - Use standardized logging configuration
7. CLEAN CODE STRUCTURE - Follow project organization

## File Structure Rules
- Keep files in appropriate directories (models/, routes/, etc.)
- Use __init__.py files in Python packages
- Follow the defined project structure
- No ad-hoc file creation

## Error Handling Pattern
```python
try:
    # Operation
    result = external_call()
except SpecificException as e:
    logging.error(f"[MODULE] Specific error: {str(e)}", exc_info=True)
    # Handle gracefully
except Exception as e:
    logging.error(f"[MODULE] Unexpected error: {str(e)}", exc_info=True)
    # Maintain system stability
finally:
    # Always cleanup
```

## Logging Pattern
```python
logging.info("[CATEGORY] Action description")
logging.error("[CATEGORY] Error description: {error}")
```

## Configuration Management
- Use config.py for application settings
- Use .env for environment variables
- No hardcoded values in code