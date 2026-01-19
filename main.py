"""
Main entry point for the Scientific Paper Summarizing Agent.

Provides a command-line interface for processing scientific papers.
"""

from pathlib import Path
from typing import Optional
import sys

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    # Fallback if rich/click not installed yet
    click = None
    Console = None

from src.agent import SummarizingAgent
from src.utils.logger import logger, setup_logger
from config.settings import settings


# Rich console for beautiful output
console = Console() if Console else None


def print_welcome():
    """Print welcome message."""
    if console:
        console.print(Panel.fit(
            "[bold cyan]Scientific Paper Summarizing Agent[/bold cyan]\n"
            "[dim]Powered by Google's Generative AI[/dim]",
            border_style="cyan"
        ))
    else:
        print("\n" + "="*60)
        print("Scientific Paper Summarizing Agent")
        print("Powered by Google's Generative AI")
        print("="*60 + "\n")


def print_summary_preview(summary):
    """Print a preview of the generated summary."""
    if console:
        table = Table(title="Summary Preview", border_style="green")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        table.add_row("Title", summary.title)
        table.add_row("Word Count", str(summary.word_count))
        table.add_row("Key Findings", str(len(summary.key_findings)))
        
        console.print(table)
        
        console.print("\n[bold green]Overview:[/bold green]")
        console.print(summary.overview)
        
        console.print("\n[bold green]Key Findings:[/bold green]")
        for i, finding in enumerate(summary.key_findings, 1):
            console.print(f"  {i}. {finding}")
    else:
        print("\n" + "="*60)
        print(f"Title: {summary.title}")
        print(f"Word Count: {summary.word_count}")
        print(f"Key Findings: {len(summary.key_findings)}")
        print("="*60 + "\n")
        
        print("Overview:")
        print(summary.overview)
        
        print("\nKey Findings:")
        for i, finding in enumerate(summary.key_findings, 1):
            print(f"  {i}. {finding}")


if click:
    @click.command()
    @click.option(
        '--file', '-f',
        type=click.Path(exists=True, path_type=Path),
        help='Path to a single paper file to summarize'
    )
    @click.option(
        '--directory', '-d',
        type=click.Path(exists=True, file_okay=False, path_type=Path),
        help='Path to directory containing papers'
    )
    @click.option(
        '--recursive', '-r',
        is_flag=True,
        help='Process directories recursively'
    )
    @click.option(
        '--title', '-t',
        type=str,
        help='Paper title (auto-detected if not provided)'
    )
    @click.option(
        '--output', '-o',
        type=click.Path(path_type=Path),
        help='Custom output directory'
    )
    @click.option(
        '--model', '-m',
        type=str,
        help='Google Gemini model to use'
    )
    @click.option(
        '--no-save',
        is_flag=True,
        help='Don\'t save output to file (print only)'
    )
    @click.option(
        '--verbose', '-v',
        is_flag=True,
        help='Enable verbose logging'
    )
    def main(
        file: Optional[Path],
        directory: Optional[Path],
        recursive: bool,
        title: Optional[str],
        output: Optional[Path],
        model: Optional[str],
        no_save: bool,
        verbose: bool
    ):
        """
        Scientific Paper Summarizing Agent using Google's ADK.
        
        Process scientific papers and generate comprehensive summaries
        with key findings, methodology, and conclusions.
        
        Examples:
        
            # Summarize a single paper
            python main.py --file paper.pdf
            
            # Batch process a directory
            python main.py --directory papers/ --recursive
            
            # Use a specific model
            python main.py --file paper.pdf --model gemini-1.5-pro-latest
        """
        # Set up logging
        if verbose:
            setup_logger(level=10)  # DEBUG
        
        print_welcome()
        
        # Validate inputs
        if not file and not directory:
            if console:
                console.print("[red]Error: Provide either --file or --directory[/red]")
            else:
                print("Error: Provide either --file or --directory")
            sys.exit(1)
        
        if file and directory:
            if console:
                console.print("[yellow]Warning: Both file and directory provided. Using file only.[/yellow]")
            else:
                print("Warning: Both file and directory provided. Using file only.")
        
        # Check API key
        if not settings.validate_api_key():
            if console:
                console.print("[red]Error: GOOGLE_API_KEY not set![/red]")
                console.print("Set it with: export GOOGLE_API_KEY='your-key-here'")
            else:
                print("Error: GOOGLE_API_KEY not set!")
                print("Set it with: export GOOGLE_API_KEY='your-key-here'")
            sys.exit(1)
        
        try:
            # Initialize agent
            agent = SummarizingAgent(
                model_name=model,
                output_dir=output
            )
            
            # Process file or directory
            if file:
                summary = agent.process_paper(
                    file,
                    title=title,
                    save_output=not no_save
                )
                print_summary_preview(summary)
                
            elif directory:
                summaries = agent.process_directory(
                    directory,
                    recursive=recursive
                )
                
                if console:
                    console.print(f"\n[green]✓ Processed {len(summaries)} papers successfully[/green]")
                else:
                    print(f"\n✓ Processed {len(summaries)} papers successfully")
        
        except Exception as e:
            logger.error(f"Error: {e}")
            if verbose:
                logger.exception("Full traceback:")
            sys.exit(1)
    
else:
    # Fallback main without click
    def main():
        print("Please install dependencies first:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


def run_example():
    """
    Run a simple example for testing.
    
    This function demonstrates basic usage without CLI arguments.
    """
    print_welcome()
    
    # Check for sample file
    sample_file = Path("data/sample_paper.txt")
    if not sample_file.exists():
        print(f"\nNo sample file found at {sample_file}")
        print("Please provide a paper using: python main.py --file your_paper.pdf")
        return
    
    print(f"Processing sample file: {sample_file}")
    
    try:
        agent = SummarizingAgent()
        summary = agent.process_paper(sample_file)
        print_summary_preview(summary)
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.exception("Full traceback:")


if __name__ == "__main__":
    if click:
        main()
    else:
        run_example()
