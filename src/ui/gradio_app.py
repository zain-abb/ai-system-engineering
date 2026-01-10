"""Gradio web interface for SE-Agent."""

import logging
from typing import Optional, Tuple

import gradio as gr

from src.config import config
from src.agent import AgentController, create_agent
from src.capabilities.base import CapabilityType
from src.evaluation import (
    quick_evaluate,
    EvaluationType,
    Severity,
)

logger = logging.getLogger(__name__)

# Global agent instance
_agent: Optional[AgentController] = None


def get_agent() -> AgentController:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        try:
            config.validate()
            _agent = create_agent(use_llm_routing=True)
            logger.info("Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    return _agent


def generate_code(
    requirements: str,
    language: str,
    context: str
) -> Tuple[str, str]:
    """Generate code from requirements."""
    if not requirements.strip():
        return "", "Please enter requirements"

    try:
        agent = get_agent()
        response = agent.generate_code(
            requirements=requirements,
            language=language,
            context=context if context.strip() else None
        )

        if response.success:
            usage_info = f"Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}"
            return response.result, usage_info
        else:
            return "", f"Error: {response.error}"

    except Exception as e:
        logger.error(f"Code generation error: {e}")
        return "", f"Error: {str(e)}"


def generate_tests(
    code: str,
    language: str,
    framework: str
) -> Tuple[str, str]:
    """Generate tests for code."""
    if not code.strip():
        return "", "Please enter code to test"

    try:
        agent = get_agent()
        response = agent.generate_tests(
            code=code,
            language=language,
            framework=framework
        )

        if response.success:
            usage_info = f"Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}"
            return response.result, usage_info
        else:
            return "", f"Error: {response.error}"

    except Exception as e:
        logger.error(f"Test generation error: {e}")
        return "", f"Error: {str(e)}"


def review_code(
    code: str,
    language: str,
    focus: str
) -> Tuple[str, str]:
    """Review code for issues."""
    if not code.strip():
        return "", "Please enter code to review"

    try:
        agent = get_agent()
        response = agent.review_code(
            code=code,
            language=language,
            focus=focus if focus.strip() else None
        )

        if response.success:
            usage_info = f"Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}"
            return response.result, usage_info
        else:
            return "", f"Error: {response.error}"

    except Exception as e:
        logger.error(f"Code review error: {e}")
        return "", f"Error: {str(e)}"


def analyze_requirements(
    requirements: str,
    context: str
) -> Tuple[str, str]:
    """Analyze software requirements."""
    if not requirements.strip():
        return "", "Please enter requirements to analyze"

    try:
        agent = get_agent()
        response = agent.process(
            user_input=requirements,
            context=context if context.strip() else None,
            force_capability=CapabilityType.REQUIREMENTS
        )

        if response.success:
            usage_info = f"Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}"
            return response.result, usage_info
        else:
            return "", f"Error: {response.error}"

    except Exception as e:
        logger.error(f"Requirements analysis error: {e}")
        return "", f"Error: {str(e)}"


def generate_docs(
    code: str,
    language: str,
    doc_type: str
) -> Tuple[str, str]:
    """Generate documentation for code."""
    if not code.strip():
        return "", "Please enter code to document"

    try:
        agent = get_agent()
        response = agent.process(
            user_input=f"Generate {doc_type} documentation for this code:\n\n{code}",
            language=language,
            force_capability=CapabilityType.DOCUMENTATION
        )

        if response.success:
            usage_info = f"Tokens: {response.usage.get('total_tokens', 'N/A')} | Cost: ${response.usage.get('cost', 0):.4f}"
            return response.result, usage_info
        else:
            return "", f"Error: {response.error}"

    except Exception as e:
        logger.error(f"Documentation generation error: {e}")
        return "", f"Error: {str(e)}"


def evaluate_code(
    code: str,
    prompt: str
) -> Tuple[str, str, str, str, str]:
    """Evaluate generated code for quality."""
    if not code.strip():
        return "", "", "", "", "Please enter code to evaluate"

    try:
        result = quick_evaluate(code=code, prompt=prompt)

        # Format results
        correctness = ""
        robustness = ""
        safety = ""
        hallucination = ""

        for eval_type, eval_result in result.results.items():
            score_str = f"Score: {eval_result.score:.2f} | {'PASSED' if eval_result.passed else 'FAILED'}\n"
            issues_str = ""

            if eval_result.issues:
                issues_str = "Issues:\n"
                for issue in eval_result.issues[:5]:  # Limit to 5 issues
                    issues_str += f"  [{issue.severity.value}] {issue.category}: {issue.description}\n"
                    if issue.suggestion:
                        issues_str += f"    Suggestion: {issue.suggestion}\n"

            formatted = score_str + issues_str

            if eval_type == EvaluationType.CORRECTNESS:
                correctness = formatted
            elif eval_type == EvaluationType.ROBUSTNESS:
                robustness = formatted
            elif eval_type == EvaluationType.SAFETY:
                safety = formatted
            elif eval_type == EvaluationType.HALLUCINATION:
                hallucination = formatted

        summary = f"Overall Score: {result.overall_score:.2f} | {'PASSED' if result.overall_passed else 'FAILED'}"

        return correctness, robustness, safety, hallucination, summary

    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        error_msg = f"Error: {str(e)}"
        return error_msg, error_msg, error_msg, error_msg, error_msg


def auto_process(
    user_input: str,
    context: str,
    language: str
) -> Tuple[str, str, str]:
    """Auto-detect intent and process request."""
    if not user_input.strip():
        return "", "", "Please enter a request"

    try:
        agent = get_agent()
        response = agent.process(
            user_input=user_input,
            context=context if context.strip() else None,
            language=language
        )

        if response.success:
            task_type = response.capability_used.value if response.capability_used else "unknown"
            confidence = response.intent_classification.confidence if response.intent_classification else 0.0
            info = f"Task Type: {task_type} | Confidence: {confidence:.2f} | Tokens: {response.usage.get('total_tokens', 'N/A')}"
            return response.result, task_type, info
        else:
            return "", "error", f"Error: {response.error}"

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return "", "error", f"Error: {str(e)}"


def create_ui() -> gr.Blocks:
    """Create the Gradio interface."""

    with gr.Blocks(
        title="SE-Agent: AI Software Engineering Assistant",
        theme=gr.themes.Soft()
    ) as demo:
        gr.Markdown("""
        # SE-Agent: AI Software Engineering Assistant

        An AI-powered assistant for code generation, test generation, code review,
        requirements analysis, and documentation. Powered by Claude.
        """)

        with gr.Tabs():
            # Auto Mode Tab
            with gr.Tab("Auto Mode"):
                gr.Markdown("Enter any request and the agent will automatically detect the task type.")

                with gr.Row():
                    with gr.Column():
                        auto_input = gr.Textbox(
                            label="Your Request",
                            placeholder="e.g., Write a function to calculate factorial...",
                            lines=5
                        )
                        auto_context = gr.Textbox(
                            label="Context (optional)",
                            placeholder="Additional context or existing code...",
                            lines=3
                        )
                        auto_language = gr.Dropdown(
                            choices=["python", "javascript", "typescript", "java", "go", "rust"],
                            value="python",
                            label="Language"
                        )
                        auto_btn = gr.Button("Process", variant="primary")

                    with gr.Column():
                        auto_output = gr.Code(label="Result", language="python")
                        auto_task_type = gr.Textbox(label="Detected Task Type")
                        auto_info = gr.Textbox(label="Info")

                auto_btn.click(
                    auto_process,
                    inputs=[auto_input, auto_context, auto_language],
                    outputs=[auto_output, auto_task_type, auto_info]
                )

            # Code Generation Tab
            with gr.Tab("Code Generation"):
                with gr.Row():
                    with gr.Column():
                        codegen_req = gr.Textbox(
                            label="Requirements",
                            placeholder="Describe what code you need...",
                            lines=5
                        )
                        codegen_lang = gr.Dropdown(
                            choices=["python", "javascript", "typescript", "java", "go", "rust"],
                            value="python",
                            label="Language"
                        )
                        codegen_ctx = gr.Textbox(
                            label="Context (optional)",
                            placeholder="Existing code or additional context...",
                            lines=3
                        )
                        codegen_btn = gr.Button("Generate Code", variant="primary")

                    with gr.Column():
                        codegen_output = gr.Code(label="Generated Code", language="python")
                        codegen_info = gr.Textbox(label="Usage Info")

                codegen_btn.click(
                    generate_code,
                    inputs=[codegen_req, codegen_lang, codegen_ctx],
                    outputs=[codegen_output, codegen_info]
                )

            # Test Generation Tab
            with gr.Tab("Test Generation"):
                with gr.Row():
                    with gr.Column():
                        testgen_code = gr.Code(
                            label="Code to Test",
                            language="python",
                            lines=10
                        )
                        testgen_lang = gr.Dropdown(
                            choices=["python", "javascript", "typescript", "java"],
                            value="python",
                            label="Language"
                        )
                        testgen_framework = gr.Dropdown(
                            choices=["pytest", "unittest", "jest", "mocha", "junit"],
                            value="pytest",
                            label="Test Framework"
                        )
                        testgen_btn = gr.Button("Generate Tests", variant="primary")

                    with gr.Column():
                        testgen_output = gr.Code(label="Generated Tests", language="python")
                        testgen_info = gr.Textbox(label="Usage Info")

                testgen_btn.click(
                    generate_tests,
                    inputs=[testgen_code, testgen_lang, testgen_framework],
                    outputs=[testgen_output, testgen_info]
                )

            # Code Review Tab
            with gr.Tab("Code Review"):
                with gr.Row():
                    with gr.Column():
                        review_code_input = gr.Code(
                            label="Code to Review",
                            language="python",
                            lines=10
                        )
                        review_lang = gr.Dropdown(
                            choices=["python", "javascript", "typescript", "java", "go", "rust"],
                            value="python",
                            label="Language"
                        )
                        review_focus = gr.Textbox(
                            label="Focus Area (optional)",
                            placeholder="e.g., security, performance, readability..."
                        )
                        review_btn = gr.Button("Review Code", variant="primary")

                    with gr.Column():
                        review_output = gr.Markdown(label="Review Results")
                        review_info = gr.Textbox(label="Usage Info")

                review_btn.click(
                    review_code,
                    inputs=[review_code_input, review_lang, review_focus],
                    outputs=[review_output, review_info]
                )

            # Requirements Analysis Tab
            with gr.Tab("Requirements"):
                with gr.Row():
                    with gr.Column():
                        req_input = gr.Textbox(
                            label="Requirements",
                            placeholder="Enter your software requirements...",
                            lines=8
                        )
                        req_context = gr.Textbox(
                            label="Context (optional)",
                            placeholder="Project context, constraints, etc...",
                            lines=3
                        )
                        req_btn = gr.Button("Analyze Requirements", variant="primary")

                    with gr.Column():
                        req_output = gr.Markdown(label="Analysis Results")
                        req_info = gr.Textbox(label="Usage Info")

                req_btn.click(
                    analyze_requirements,
                    inputs=[req_input, req_context],
                    outputs=[req_output, req_info]
                )

            # Documentation Tab
            with gr.Tab("Documentation"):
                with gr.Row():
                    with gr.Column():
                        doc_code = gr.Code(
                            label="Code to Document",
                            language="python",
                            lines=10
                        )
                        doc_lang = gr.Dropdown(
                            choices=["python", "javascript", "typescript", "java"],
                            value="python",
                            label="Language"
                        )
                        doc_type = gr.Dropdown(
                            choices=["API", "README", "inline", "comprehensive"],
                            value="API",
                            label="Documentation Type"
                        )
                        doc_btn = gr.Button("Generate Documentation", variant="primary")

                    with gr.Column():
                        doc_output = gr.Markdown(label="Generated Documentation")
                        doc_info = gr.Textbox(label="Usage Info")

                doc_btn.click(
                    generate_docs,
                    inputs=[doc_code, doc_lang, doc_type],
                    outputs=[doc_output, doc_info]
                )

            # Evaluation Tab
            with gr.Tab("Evaluate Code"):
                gr.Markdown("""
                Evaluate generated code for:
                - **Correctness**: Syntax validity, execution success
                - **Robustness**: Edge case handling, input validation
                - **Safety**: Security vulnerabilities
                - **Hallucination**: Invalid imports, fake APIs
                """)

                with gr.Row():
                    with gr.Column():
                        eval_code = gr.Code(
                            label="Code to Evaluate",
                            language="python",
                            lines=10
                        )
                        eval_prompt = gr.Textbox(
                            label="Original Prompt (optional)",
                            placeholder="The prompt used to generate this code...",
                            lines=2
                        )
                        eval_btn = gr.Button("Evaluate", variant="primary")

                    with gr.Column():
                        eval_correctness = gr.Textbox(label="Correctness", lines=4)
                        eval_robustness = gr.Textbox(label="Robustness", lines=4)
                        eval_safety = gr.Textbox(label="Safety", lines=4)
                        eval_hallucination = gr.Textbox(label="Hallucination", lines=4)
                        eval_summary = gr.Textbox(label="Summary")

                eval_btn.click(
                    evaluate_code,
                    inputs=[eval_code, eval_prompt],
                    outputs=[eval_correctness, eval_robustness, eval_safety, eval_hallucination, eval_summary]
                )

        gr.Markdown("""
        ---
        **SE-Agent** - AI-powered Software Engineering Assistant
        Built with Claude API and Gradio
        """)

    return demo


def launch_app(
    share: bool = False,
    server_port: int = 7860,
    server_name: str = "0.0.0.0"
) -> None:
    """Launch the Gradio application."""
    demo = create_ui()
    demo.launch(
        share=share,
        server_port=server_port,
        server_name=server_name
    )


if __name__ == "__main__":
    launch_app()
