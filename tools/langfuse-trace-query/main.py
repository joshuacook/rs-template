#!/usr/bin/env python3
"""
Langfuse Trace Query Tool

Query and analyze Langfuse traces with filtering, export, and analysis capabilities.

Usage:
    uv run main.py list --limit 10
    uv run main.py search user123 --from-date 2024-01-01
    uv run main.py export --session-id session123 --format json
    uv run main.py analyze --from-date 2024-01-01
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dateutil import parser as date_parser

import typer
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv
from pydantic import BaseModel
from langfuse import Langfuse

app = typer.Typer(help="Query and analyze Langfuse traces")
console = Console()

class LangfuseConfig(BaseModel):
    """Langfuse configuration model"""
    public_key: str
    secret_key: str
    host: str = "https://cloud.langfuse.com"

class TraceQueryTool:
    """Main tool for querying Langfuse traces"""
    
    def __init__(self):
        self.config = self._load_config()
        self.client = self._init_client()
    
    def _load_config(self) -> LangfuseConfig:
        """Load Langfuse configuration from .env file"""
        
        # Load .env file from tool root
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            console.print(f"✅ Loaded configuration from {env_path}")
        else:
            console.print(f"⚠️  No .env file found at {env_path}")
            console.print("💡 Create a .env file with LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST")
        
        # Get configuration from environment
        public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        secret_key = os.getenv('LANGFUSE_SECRET_KEY')
        host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
        
        if not public_key or not secret_key:
            console.print("❌ Missing required Langfuse credentials!", style="red")
            console.print("\nRequired environment variables:")
            console.print("- LANGFUSE_PUBLIC_KEY")
            console.print("- LANGFUSE_SECRET_KEY")
            console.print("- LANGFUSE_HOST (optional, defaults to cloud.langfuse.com)")
            raise typer.Exit(1)
        
        return LangfuseConfig(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
    
    def _init_client(self) -> Langfuse:
        """Initialize Langfuse client"""
        try:
            client = Langfuse(
                public_key=self.config.public_key,
                secret_key=self.config.secret_key,
                host=self.config.host
            )
            
            # Test connection by trying to get a small number of traces
            client.api.trace.list(limit=1)
            console.print(f"✅ Connected to Langfuse at {self.config.host}")
            return client
            
        except Exception as e:
            console.print(f"❌ Failed to connect to Langfuse: {e}", style="red")
            raise typer.Exit(1)
    
    def get_traces(
        self, 
        limit: int = 50,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get traces with optional filtering"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching traces...", total=None)
            
            # Build filter parameters
            filter_params = {}
            if user_id:
                filter_params['user_id'] = user_id
            if session_id:
                filter_params['session_id'] = session_id
            if tags:
                filter_params['tags'] = tags
            
            # Parse dates
            if from_date:
                try:
                    filter_params['from_timestamp'] = date_parser.parse(from_date)
                except ValueError:
                    console.print(f"❌ Invalid from_date format: {from_date}", style="red")
                    raise typer.Exit(1)
            
            if to_date:
                try:
                    filter_params['to_timestamp'] = date_parser.parse(to_date)
                except ValueError:
                    console.print(f"❌ Invalid to_date format: {to_date}", style="red")
                    raise typer.Exit(1)
            
            # Fetch traces
            traces = []
            try:
                # Use the correct API method
                response = self.client.api.trace.list(limit=limit, **filter_params)
                
                # Extract traces from response
                trace_list = response.data if hasattr(response, 'data') else response
                
                for trace in trace_list:
                    traces.append({
                        'id': getattr(trace, 'id', None),
                        'name': getattr(trace, 'name', None),
                        'user_id': getattr(trace, 'user_id', None),
                        'session_id': getattr(trace, 'session_id', None),
                        'timestamp': getattr(trace, 'timestamp', None).isoformat() if getattr(trace, 'timestamp', None) else None,
                        'tags': getattr(trace, 'tags', []),
                        'metadata': getattr(trace, 'metadata', {}),
                        'input': getattr(trace, 'input', None),
                        'output': getattr(trace, 'output', None),
                        'level': getattr(trace, 'level', None),
                        'status_message': getattr(trace, 'status_message', None),
                        'version': getattr(trace, 'version', None),
                        'release': getattr(trace, 'release', None),
                        'public': getattr(trace, 'public', None)
                    })
                    
                    progress.update(task, description=f"Fetched {len(traces)} traces...")
                    
            except Exception as e:
                console.print(f"❌ Error fetching traces: {e}", style="red")
                raise typer.Exit(1)
            
            progress.update(task, description=f"✅ Fetched {len(traces)} traces")
        
        return traces
    
    def display_traces_table(self, traces: List[Dict[str, Any]], compact: bool = False):
        """Display traces in a formatted table"""
        
        if not traces:
            console.print("📭 No traces found")
            return
        
        table = Table(title=f"Langfuse Traces ({len(traces)} results)")
        
        if compact:
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            table.add_column("User", style="green")
            table.add_column("Timestamp", style="blue")
            
            for trace in traces:
                table.add_row(
                    trace['id'][:8] + "..." if trace['id'] else "N/A",
                    trace['name'] or "N/A",
                    trace['user_id'] or "N/A",
                    trace['timestamp'][:19] if trace['timestamp'] else "N/A"
                )
        else:
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            table.add_column("User", style="green")
            table.add_column("Session", style="yellow")
            table.add_column("Timestamp", style="blue")
            table.add_column("Tags", style="red")
            table.add_column("Level", style="white")
            
            for trace in traces:
                tags_str = ", ".join(trace['tags']) if trace['tags'] else "None"
                table.add_row(
                    trace['id'][:12] + "..." if trace['id'] else "N/A",
                    trace['name'] or "N/A",
                    trace['user_id'] or "N/A",
                    trace['session_id'][:12] + "..." if trace['session_id'] else "N/A",
                    trace['timestamp'][:19] if trace['timestamp'] else "N/A",
                    tags_str[:20] + "..." if len(tags_str) > 20 else tags_str,
                    trace['level'] or "N/A"
                )
        
        console.print(table)
    
    def export_traces(self, traces: List[Dict[str, Any]], format: str, filename: Optional[str] = None):
        """Export traces to file"""
        
        if not traces:
            console.print("📭 No traces to export")
            return
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"langfuse_traces_{timestamp}.{format}"
        
        filepath = Path(filename)
        
        try:
            if format == 'json':
                with open(filepath, 'w') as f:
                    json.dump(traces, f, indent=2, default=str)
                    
            elif format == 'csv':
                # Flatten traces for CSV export
                flattened_traces = []
                for trace in traces:
                    flat_trace = {
                        'id': trace['id'],
                        'name': trace['name'],
                        'user_id': trace['user_id'],
                        'session_id': trace['session_id'],
                        'timestamp': trace['timestamp'],
                        'level': trace['level'],
                        'status_message': trace['status_message'],
                        'version': trace['version'],
                        'release': trace['release'],
                        'tags': ', '.join(trace['tags']) if trace['tags'] else '',
                        'input_preview': str(trace['input'])[:100] if trace['input'] else '',
                        'output_preview': str(trace['output'])[:100] if trace['output'] else '',
                    }
                    flattened_traces.append(flat_trace)
                
                df = pd.DataFrame(flattened_traces)
                df.to_csv(filepath, index=False)
                
            elif format == 'xlsx':
                df = pd.DataFrame(traces)
                df.to_excel(filepath, index=False)
                
            else:
                console.print(f"❌ Unsupported export format: {format}", style="red")
                return
                
            console.print(f"✅ Exported {len(traces)} traces to {filepath}")
            
        except Exception as e:
            console.print(f"❌ Export failed: {e}", style="red")
    
    def analyze_traces(self, traces: List[Dict[str, Any]]):
        """Analyze traces and show metrics"""
        
        if not traces:
            console.print("📭 No traces to analyze")
            return
        
        console.print("\n📊 Trace Analysis", style="bold blue")
        
        # Basic metrics
        total_traces = len(traces)
        unique_users = len(set(t['user_id'] for t in traces if t['user_id']))
        unique_sessions = len(set(t['session_id'] for t in traces if t['session_id']))
        
        # Metrics table
        metrics_table = Table(title="Basic Metrics")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green")
        
        metrics_table.add_row("Total Traces", str(total_traces))
        metrics_table.add_row("Unique Users", str(unique_users))
        metrics_table.add_row("Unique Sessions", str(unique_sessions))
        
        # Time range
        timestamps = [t['timestamp'] for t in traces if t['timestamp']]
        if timestamps:
            earliest = min(timestamps)
            latest = max(timestamps)
            metrics_table.add_row("Time Range", f"{earliest[:19]} to {latest[:19]}")
        
        console.print(metrics_table)
        
        # Top users
        if unique_users > 0:
            user_counts = {}
            for trace in traces:
                if trace['user_id']:
                    user_counts[trace['user_id']] = user_counts.get(trace['user_id'], 0) + 1
            
            top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            users_table = Table(title="Top Users")
            users_table.add_column("User ID", style="cyan")
            users_table.add_column("Trace Count", style="green")
            
            for user_id, count in top_users:
                users_table.add_row(user_id, str(count))
            
            console.print(users_table)

@app.command()
def list(
    limit: int = typer.Option(50, help="Maximum number of traces to fetch"),
    compact: bool = typer.Option(False, help="Show compact table format"),
    user_id: Optional[str] = typer.Option(None, help="Filter by user ID"),
    session_id: Optional[str] = typer.Option(None, help="Filter by session ID"),
    from_date: Optional[str] = typer.Option(None, help="Filter traces from date (YYYY-MM-DD or ISO format)"),
    to_date: Optional[str] = typer.Option(None, help="Filter traces to date (YYYY-MM-DD or ISO format)"),
    tags: Optional[List[str]] = typer.Option(None, help="Filter by tags")
):
    """List traces with optional filtering"""
    
    tool = TraceQueryTool()
    traces = tool.get_traces(
        limit=limit,
        user_id=user_id,
        session_id=session_id,
        from_date=from_date,
        to_date=to_date,
        tags=tags
    )
    
    tool.display_traces_table(traces, compact=compact)

@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (user_id, session_id, or tag)"),
    limit: int = typer.Option(50, help="Maximum number of traces to fetch"),
    from_date: Optional[str] = typer.Option(None, help="Filter traces from date"),
    to_date: Optional[str] = typer.Option(None, help="Filter traces to date")
):
    """Search traces by user, session, or tag"""
    
    tool = TraceQueryTool()
    
    # Try different search strategies
    console.print(f"🔍 Searching for: {query}")
    
    # Search by user_id
    traces = tool.get_traces(
        limit=limit,
        user_id=query,
        from_date=from_date,
        to_date=to_date
    )
    
    if not traces:
        # Search by session_id
        traces = tool.get_traces(
            limit=limit,
            session_id=query,
            from_date=from_date,
            to_date=to_date
        )
    
    if not traces:
        # Search by tag
        traces = tool.get_traces(
            limit=limit,
            tags=[query],
            from_date=from_date,
            to_date=to_date
        )
    
    tool.display_traces_table(traces)

@app.command()
def export(
    format: str = typer.Option("json", help="Export format: json, csv, xlsx"),
    filename: Optional[str] = typer.Option(None, help="Output filename"),
    limit: int = typer.Option(100, help="Maximum number of traces to export"),
    user_id: Optional[str] = typer.Option(None, help="Filter by user ID"),
    session_id: Optional[str] = typer.Option(None, help="Filter by session ID"),
    from_date: Optional[str] = typer.Option(None, help="Filter traces from date"),
    to_date: Optional[str] = typer.Option(None, help="Filter traces to date")
):
    """Export traces to file"""
    
    tool = TraceQueryTool()
    traces = tool.get_traces(
        limit=limit,
        user_id=user_id,
        session_id=session_id,
        from_date=from_date,
        to_date=to_date
    )
    
    tool.export_traces(traces, format, filename)

@app.command()
def analyze(
    limit: int = typer.Option(1000, help="Maximum number of traces to analyze"),
    user_id: Optional[str] = typer.Option(None, help="Filter by user ID"),
    from_date: Optional[str] = typer.Option(None, help="Filter traces from date"),
    to_date: Optional[str] = typer.Option(None, help="Filter traces to date")
):
    """Analyze traces and show metrics"""
    
    tool = TraceQueryTool()
    traces = tool.get_traces(
        limit=limit,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date
    )
    
    tool.analyze_traces(traces)

@app.command()
def config():
    """Show current configuration"""
    
    try:
        tool = TraceQueryTool()
        console.print("📋 Current Configuration:", style="bold blue")
        console.print(f"Host: {tool.config.host}")
        console.print(f"Public Key: {tool.config.public_key[:10]}...")
        console.print(f"Secret Key: [HIDDEN]")
        console.print("✅ Configuration is valid")
        
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")

if __name__ == "__main__":
    app()