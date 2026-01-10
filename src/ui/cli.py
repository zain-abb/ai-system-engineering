"""Command-line interface for SE-Agent."""

import sys
import json
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import config
from src.agent import AgentController, create_agent
from src.capabilities.base import CapabilityType
from src.evaluation import (
    quick_evaluate,
    generate_evaluation_report,
    EvaluationType,
)

console = Console()
logger = logging.getLogger(__name__)

# Global agent
_agent: Optional[AgentController] = None


def get_agent() -> AgentController:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        with console.status("[bold green]Initializing SE-Agent..."):
            try:
                config.validate()
                _agent = create_agent(use_llm_routing=True)
            except Exception as e:
                console.print(f"[red]Failed to initialize agent: {e}[/red]")
                raise
    return _agent


def display_result(result: str, title: str = "Result", language: str = "python") -> None:
    """Display a result with syntax highlighting."""
    # Check if result looks like code
    code_indicators = ["def ", "class ", "import ", "function ", "const ", "let ", "var "]
    is_code = any(ind in result for ind in code_indicators)

    if is_code:
        syntax = Syntax(result, language, theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=title))
    else:
        console.print(Panel(Markdown(result), title=title))


def display_evaluation(eval_result) -> None:
    """Display evaluation results in a formatted table."""
    table = Table(title="Evaluation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Issues", style="yellow")

    for eval_type, result in eval_result.results.items():
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        issues = str(len(result.issues))
        table.add_row(
            eval_type.value,
            f"{result.score:.2f}",
            status,
            issues
        )

    console.print(table)

    # Show overall score
    overall_status = "[green]PASSED[/green]" if eval_result.overall_passed else "[red]FAILED[/red]"
    console.print(f"\n[bold]Overall Score:[/bold] {eval_result.overall_score:.2f} {overall_status}")

    # Show top issues
    all_issues = []
    for result in eval_result.results.values():
        all_issues.extend(result.issues)

    if all_issues:
        console.print("\n[bold]Top Issues:[/bold]")
        for issue in all_issues[:5]:
            severity_color = {
                "critical": "red",
                "high": "red",
                "medium": "yellow",
                "low": "blue",
                "info": "white"
            }.get(issue.severity.value, "white")

            console.print(f"  [{severity_color}][{issue.severity.value}][/{severity_color}] {issue.category}: {issue.description}")
            if issue.suggestion:
                console.print(f"    [dim]Suggestion: {issue.suggestion}[/dim]")


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """SE-Agent: AI-powered Software Engineering Assistant."""
    pass


@cli.command()
@click.argument("prompt")
@click.option("--language", "-l", default="python", help="Programming language")
@click.option("--context", "-c", default="", help="Additional context")
@click.option("--output", "-o", help="Output file path")
def generate(prompt: str, language: str, context: str, output: Optional[str]):
    """Generate code from a natural language prompt."""
    try:
        agent = get_agent()

        with console.status("[bold green]Generating code..."):
            response = agent.generate_code(
                requirements=prompt,
                language=language,
                context=context if context else None
            )

        if response.success:
            display_result(response.result, "Generated Code", language)

            if output:
                Path(output).write_text(response.result)
                console.print(f"[green]Code saved to {output}[/green]")

            # Show usage
            if response.usage:
                console.print(f"\n[dim]Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}[/dim]")
        else:
            console.print(f"[red]Error: {response.error}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("code_file", type=click.Path(exists=True))
@click.option("--language", "-l", default="python", help="Programming language")
@click.option("--framework", "-f", default="pytest", help="Test framework")
@click.option("--output", "-o", help="Output file path")
def test(code_file: str, language: str, framework: str, output: Optional[str]):
    """Generate tests for code in a file."""
    try:
        code = Path(code_file).read_text()
        agent = get_agent()

        with console.status("[bold green]Generating tests..."):
            response = agent.generate_tests(
                code=code,
                language=language,
                framework=framework
            )

        if response.success:
            display_result(response.result, "Generated Tests", language)

            if output:
                Path(output).write_text(response.result)
                console.print(f"[green]Tests saved to {output}[/green]")

            if response.usage:
                console.print(f"\n[dim]Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}[/dim]")
        else:
            console.print(f"[red]Error: {response.error}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("code_file", type=click.Path(exists=True))
@click.option("--language", "-l", default="python", help="Programming language")
@click.option("--focus", "-f", default="", help="Focus area (security, performance, readability)")
def review(code_file: str, language: str, focus: str):
    """Review code in a file for issues and improvements."""
    try:
        code = Path(code_file).read_text()
        agent = get_agent()

        with console.status("[bold green]Reviewing code..."):
            response = agent.review_code(
                code=code,
                language=language,
                focus=focus if focus else None
            )

        if response.success:
            display_result(response.result, "Code Review", "markdown")

            if response.usage:
                console.print(f"\n[dim]Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}[/dim]")
        else:
            console.print(f"[red]Error: {response.error}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("code_file", type=click.Path(exists=True))
@click.option("--prompt", "-p", default="", help="Original prompt used to generate the code")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def evaluate(code_file: str, prompt: str, json_output: bool):
    """Evaluate code for correctness, safety, robustness, and hallucinations."""
    try:
        code = Path(code_file).read_text()

        with console.status("[bold green]Evaluating code..."):
            result = quick_evaluate(code=code, prompt=prompt)

        if json_output:
            console.print(json.dumps(result.to_dict(), indent=2))
        else:
            display_evaluation(result)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--extensions", "-e", multiple=True, default=[".py"], help="File extensions to index")
def index(directory: str, extensions: tuple):
    """Index a codebase for RAG retrieval."""
    try:
        agent = get_agent()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Indexing codebase...", total=None)
            chunk_count = agent.index_codebase(
                directory=directory,
                extensions=list(extensions)
            )
            progress.update(task, completed=True)

        console.print(f"[green]Indexed {chunk_count} chunks from {directory}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--results", "-n", default=5, help="Number of results")
@click.option("--language", "-l", default="", help="Filter by language")
def search(query: str, results: int, language: str):
    """Search indexed codebase for relevant code."""
    try:
        agent = get_agent()

        if not agent.retriever:
            console.print("[red]RAG not available. Index a codebase first.[/red]")
            return

        with console.status("[bold green]Searching..."):
            filter_dict = {"language": language} if language else None
            search_result = agent.retriever.retrieve(
                query=query,
                n_results=results,
                filter_dict=filter_dict
            )

        if not search_result.results:
            console.print("[yellow]No results found.[/yellow]")
            return

        for i, r in enumerate(search_result.results, 1):
            console.print(Panel(
                Syntax(r.content, "python", theme="monokai"),
                title=f"[{i}] {r.name} ({r.file_path})",
                subtitle=f"Score: {r.score:.3f} | Type: {r.chunk_type}"
            ))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("prompt")
@click.option("--context", "-c", default="", help="Additional context")
@click.option("--language", "-l", default="python", help="Programming language")
def ask(prompt: str, context: str, language: str):
    """Ask any question - agent will auto-detect the task type."""
    try:
        agent = get_agent()

        with console.status("[bold green]Processing..."):
            response = agent.process(
                user_input=prompt,
                context=context if context else None,
                language=language
            )

        if response.success:
            task_type = response.capability_used.value if response.capability_used else "unknown"
            confidence = response.intent_classification.confidence if response.intent_classification else 0.0

            console.print(f"[dim]Detected task: {task_type} (confidence: {confidence:.2f})[/dim]\n")
            display_result(response.result, f"Result ({task_type})", language)

            if response.usage:
                console.print(f"\n[dim]Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}[/dim]")
        else:
            console.print(f"[red]Error: {response.error}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def usage():
    """Show API usage statistics."""
    try:
        agent = get_agent()
        stats = agent.get_usage_stats()

        table = Table(title="API Usage Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Requests", str(stats.get("total_requests", 0)))
        table.add_row("Total Tokens", str(stats.get("total_tokens", 0)))
        table.add_row("Input Tokens", str(stats.get("input_tokens", 0)))
        table.add_row("Output Tokens", str(stats.get("output_tokens", 0)))
        table.add_row("Total Cost", f"${stats.get('total_cost', 0):.4f}")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("dataset_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="evaluation_report.json", help="Output report file")
def batch_evaluate(dataset_file: str, output: str):
    """Run batch evaluation on a dataset file (JSON with list of tasks)."""
    try:
        # Load dataset
        with open(dataset_file, 'r') as f:
            tasks = json.load(f)

        console.print(f"[bold]Evaluating {len(tasks)} tasks...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            eval_task = progress.add_task(f"Evaluating 0/{len(tasks)}...", total=len(tasks))

            def update_progress(current, total):
                progress.update(eval_task, completed=current, description=f"Evaluating {current}/{total}...")

            report = generate_evaluation_report(tasks, output_path=output)
            progress.update(eval_task, completed=len(tasks))

        # Display summary
        summary = report.summary
        console.print("\n[bold]Evaluation Summary:[/bold]")
        console.print(f"  Total tasks: {summary['total_tasks']}")
        console.print(f"  Passed: [green]{summary['passed_tasks']}[/green]")
        console.print(f"  Failed: [red]{summary['failed_tasks']}[/red]")
        console.print(f"  Pass rate: {summary['pass_rate']:.1%}")
        console.print(f"  Average score: {summary['average_overall_score']:.2f}")
        console.print(f"\n[green]Report saved to {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def interactive():
    """Start an interactive session."""
    console.print("[bold]SE-Agent Interactive Mode[/bold]")
    console.print("Type your requests, or use commands: /generate, /test, /review, /evaluate, /quit\n")

    agent = get_agent()
    language = "python"

    while True:
        try:
            user_input = console.input("[bold cyan]>>> [/bold cyan]")

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.split()[0].lower()

                if cmd == "/quit" or cmd == "/exit":
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                elif cmd == "/lang":
                    parts = user_input.split()
                    if len(parts) > 1:
                        language = parts[1]
                        console.print(f"Language set to: {language}")
                    else:
                        console.print(f"Current language: {language}")
                    continue
                elif cmd == "/usage":
                    stats = agent.get_usage_stats()
                    console.print(f"Requests: {stats.get('total_requests', 0)} | Cost: ${stats.get('total_cost', 0):.4f}")
                    continue
                elif cmd == "/help":
                    console.print("""
Commands:
  /lang <language>  - Set programming language
  /usage           - Show usage statistics
  /quit            - Exit interactive mode
  /help            - Show this help

Just type your request to auto-detect the task type.
                    """)
                    continue

            # Process request
            with console.status("[bold green]Processing..."):
                response = agent.process(
                    user_input=user_input,
                    language=language
                )

            if response.success:
                task_type = response.capability_used.value if response.capability_used else "unknown"
                console.print(f"\n[dim]({task_type})[/dim]")
                display_result(response.result, "Result", language)
            else:
                console.print(f"[red]Error: {response.error}[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
