# Langfuse Trace Query Tool

A comprehensive command-line tool for querying, analyzing, and exporting traces from Langfuse with filtering, search, and data analysis capabilities.

## Features

- **Query Traces**: List traces with advanced filtering by user, session, dates, and tags
- **Search Functionality**: Search by user ID, session ID, or tags with fallback strategies
- **Export Capabilities**: Export traces to JSON, CSV, or XLSX formats
- **Analysis Tools**: Generate metrics and insights from trace data
- **Rich CLI Interface**: Beautiful terminal output with tables and progress indicators
- **Configuration Management**: Secure credential storage via environment variables

## Installation

```bash
cd tools/langfuse-trace-query
uv sync
```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Langfuse credentials:
   ```bash
   # Required
   LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
   LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
   
   # Optional (defaults to cloud.langfuse.com)
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

3. Verify configuration:
   ```bash
   uv run main.py config
   ```

## Usage

### List Traces

```bash
# List recent traces (default: 50)
uv run main.py list

# List with filtering
uv run main.py list --user-id user123 --limit 100
uv run main.py list --from-date 2024-01-01 --to-date 2024-01-31
uv run main.py list --session-id session456 --compact

# Filter by tags
uv run main.py list --tags production --tags api-call
```

### Search Traces

```bash
# Smart search (tries user_id, then session_id, then tags)
uv run main.py search user123
uv run main.py search session456
uv run main.py search production

# Search with date filtering
uv run main.py search user123 --from-date 2024-01-01
```

### Export Traces

```bash
# Export to JSON (default)
uv run main.py export --limit 1000 --filename traces.json

# Export to CSV
uv run main.py export --format csv --user-id user123

# Export to Excel
uv run main.py export --format xlsx --from-date 2024-01-01

# Export with filtering
uv run main.py export --format csv --session-id session456 --limit 500
```

### Analyze Traces

```bash
# Basic analysis
uv run main.py analyze

# Analyze specific user
uv run main.py analyze --user-id user123

# Analyze date range
uv run main.py analyze --from-date 2024-01-01 --to-date 2024-01-31
```

## Command Reference

### `list` - List traces with filtering

Options:
- `--limit INTEGER`: Maximum number of traces (default: 50)
- `--compact`: Show compact table format
- `--user-id TEXT`: Filter by user ID
- `--session-id TEXT`: Filter by session ID
- `--from-date TEXT`: Filter from date (YYYY-MM-DD or ISO format)
- `--to-date TEXT`: Filter to date (YYYY-MM-DD or ISO format)
- `--tags TEXT`: Filter by tags (can be used multiple times)

### `search` - Search traces by query

Arguments:
- `query`: Search term (user_id, session_id, or tag)

Options:
- `--limit INTEGER`: Maximum number of traces (default: 50)
- `--from-date TEXT`: Filter from date
- `--to-date TEXT`: Filter to date

### `export` - Export traces to file

Options:
- `--format TEXT`: Export format (json, csv, xlsx) [default: json]
- `--filename TEXT`: Output filename (auto-generated if not provided)
- `--limit INTEGER`: Maximum traces to export (default: 100)
- `--user-id TEXT`: Filter by user ID
- `--session-id TEXT`: Filter by session ID
- `--from-date TEXT`: Filter from date
- `--to-date TEXT`: Filter to date

### `analyze` - Analyze traces and show metrics

Options:
- `--limit INTEGER`: Maximum traces to analyze (default: 1000)
- `--user-id TEXT`: Filter by user ID
- `--from-date TEXT`: Filter from date
- `--to-date TEXT`: Filter to date

### `config` - Show current configuration

Displays masked credentials and connection status.

## Output Formats

### Table Display

The tool displays traces in rich tables with the following information:
- **Compact mode**: ID, Name, User, Timestamp
- **Full mode**: ID, Name, User, Session, Timestamp, Tags, Level

### Export Formats

#### JSON Export
- Complete trace data with all fields
- Preserves complex data structures
- Best for programmatic processing

#### CSV Export
- Flattened trace data for spreadsheet analysis
- Input/output previews (100 chars)
- Tags joined as comma-separated values

#### XLSX Export
- Excel-compatible format
- Preserves data types where possible
- Good for business reporting

## Examples

### Daily Trace Analysis
```bash
# Get today's traces for analysis
uv run main.py analyze --from-date $(date +%Y-%m-%d)

# Export yesterday's traces
uv run main.py export --format xlsx --from-date $(date -d yesterday +%Y-%m-%d)
```

### User Activity Investigation
```bash
# Find all traces for a specific user
uv run main.py search user123

# Get detailed analysis for that user
uv run main.py analyze --user-id user123 --limit 5000

# Export user's traces for further analysis
uv run main.py export --format csv --user-id user123 --filename user123_traces.csv
```

### Production Monitoring
```bash
# Check recent production traces
uv run main.py list --tags production --limit 100

# Analyze production traces from last week
uv run main.py analyze --tags production --from-date 2024-01-20 --to-date 2024-01-27
```

## Error Handling

The tool provides clear error messages for common issues:

- **Missing credentials**: Shows required environment variables
- **Connection failures**: Displays connection error details
- **Invalid dates**: Explains expected date formats
- **No traces found**: Indicates search returned no results

## Development

### Adding New Features

1. Add new commands to the `main.py` file using Typer decorators
2. Extend the `TraceQueryTool` class with new methods
3. Update this README with usage examples

### Testing

```bash
# Test configuration
uv run main.py config

# Test basic connectivity
uv run main.py list --limit 1
```

## Troubleshooting

### Common Issues

**"No .env file found"**
- Copy `.env.example` to `.env` and add your credentials

**"Missing required Langfuse credentials"**
- Ensure `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set in `.env`

**"Failed to connect to Langfuse"**
- Check your credentials and network connectivity
- Verify `LANGFUSE_HOST` is correct (defaults to cloud.langfuse.com)

**"No traces found"**
- Try broader search criteria
- Check date ranges and filters
- Verify you have access to traces in the Langfuse project

### Debug Mode

For detailed error information, you can examine the rich console output which shows:
- Connection status
- Query parameters
- Progress indicators
- Detailed error messages

## Security

- Credentials are stored in `.env` file (not committed to git)
- Secret keys are masked in configuration display
- No credentials are logged or exposed in output