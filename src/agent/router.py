"""Intent router for classifying user requests and routing to appropriate capabilities."""

import logging
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass

from src.capabilities.base import CapabilityType
from src.services.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# Keywords for simple rule-based classification
INTENT_KEYWORDS = {
    CapabilityType.CODE_GENERATION: [
        "generate", "create", "write", "implement", "build", "make",
        "code", "function", "class", "script", "program"
    ],
    CapabilityType.TEST_GENERATION: [
        "test", "tests", "testing", "unittest", "pytest", "spec",
        "coverage", "test case", "test suite"
    ],
    CapabilityType.CODE_REVIEW: [
        "review", "check", "analyze", "find bugs", "security",
        "vulnerability", "improve", "refactor", "issues"
    ],
    CapabilityType.REQUIREMENTS: [
        "requirements", "specs", "specification", "user story",
        "acceptance criteria", "feature", "needs"
    ],
    CapabilityType.DOCUMENTATION: [
        "document", "documentation", "docstring", "readme",
        "explain", "describe", "api doc", "tutorial"
    ],
}


@dataclass
class IntentClassification:
    """Result of intent classification."""
    primary_intent: CapabilityType
    confidence: float  # 0.0 to 1.0
    secondary_intents: List[Tuple[CapabilityType, float]]
    reasoning: str


class IntentRouter:
    """Routes user requests to appropriate capabilities based on intent."""

    def __init__(self, client: Optional[ClaudeClient] = None, use_llm: bool = True):
        """
        Initialize the intent router.

        Args:
            client: Optional Claude client for LLM-based classification
            use_llm: Whether to use LLM for classification (vs rule-based only)
        """
        self.client = client
        self.use_llm = use_llm and client is not None
        self.logger = logging.getLogger(self.__class__.__name__)

    def classify(self, user_input: str) -> IntentClassification:
        """
        Classify the user's intent.

        Args:
            user_input: The user's request text

        Returns:
            IntentClassification with primary intent and confidence
        """
        # First, try rule-based classification
        rule_result = self._rule_based_classify(user_input)

        # If confidence is high enough, use rule-based result
        if rule_result.confidence >= 0.8:
            return rule_result

        # Otherwise, use LLM for more accurate classification
        if self.use_llm:
            try:
                llm_result = self._llm_classify(user_input)
                # Combine rule-based and LLM results
                return self._combine_classifications(rule_result, llm_result)
            except Exception as e:
                self.logger.warning(f"LLM classification failed, using rules: {e}")
                return rule_result

        return rule_result

    def _rule_based_classify(self, user_input: str) -> IntentClassification:
        """Classify intent using keyword matching."""
        input_lower = user_input.lower()
        scores = {}

        for capability_type, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in input_lower)
            # Boost score for exact phrase matches
            score += sum(2 for kw in keywords if re.search(rf"\b{kw}\b", input_lower))
            scores[capability_type] = score

        # Sort by score
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if sorted_intents[0][1] == 0:
            # No keywords matched, default to code generation
            return IntentClassification(
                primary_intent=CapabilityType.CODE_GENERATION,
                confidence=0.3,
                secondary_intents=[],
                reasoning="No keywords matched, defaulting to code generation"
            )

        # Calculate confidence based on score difference
        total_score = sum(s for _, s in sorted_intents if s > 0)
        primary_score = sorted_intents[0][1]
        confidence = min(0.9, primary_score / max(total_score, 1) * 0.8 + 0.2)

        secondary = [
            (intent, score / max(total_score, 1))
            for intent, score in sorted_intents[1:3]
            if score > 0
        ]

        return IntentClassification(
            primary_intent=sorted_intents[0][0],
            confidence=confidence,
            secondary_intents=secondary,
            reasoning=f"Keyword match: {sorted_intents[0][1]} matches for {sorted_intents[0][0].value}"
        )

    def _llm_classify(self, user_input: str) -> IntentClassification:
        """Classify intent using Claude."""
        if not self.client:
            raise ValueError("No Claude client available for LLM classification")

        system_prompt = """You are an intent classifier for a software engineering assistant.
Classify the user's request into one of these categories:
- code_generation: User wants to generate/create/write new code
- test_generation: User wants to create tests for code
- code_review: User wants code reviewed for bugs, security, or quality
- requirements: User wants requirements analysis or generation
- documentation: User wants documentation generated

Respond with ONLY the category name, nothing else."""

        response = self.client.generate(
            prompt=f"Classify this request: {user_input}",
            system_prompt=system_prompt,
            model="claude-3-haiku-20240307",  # Use fast model for classification
            max_tokens=50,
            temperature=0.0
        )

        response_lower = response.strip().lower()

        # Map response to capability type
        mapping = {
            "code_generation": CapabilityType.CODE_GENERATION,
            "test_generation": CapabilityType.TEST_GENERATION,
            "code_review": CapabilityType.CODE_REVIEW,
            "requirements": CapabilityType.REQUIREMENTS,
            "documentation": CapabilityType.DOCUMENTATION,
        }

        for key, capability in mapping.items():
            if key in response_lower:
                return IntentClassification(
                    primary_intent=capability,
                    confidence=0.85,
                    secondary_intents=[],
                    reasoning=f"LLM classified as: {key}"
                )

        # Fallback
        return IntentClassification(
            primary_intent=CapabilityType.CODE_GENERATION,
            confidence=0.5,
            secondary_intents=[],
            reasoning="LLM classification unclear, defaulting to code generation"
        )

    def _combine_classifications(
        self,
        rule_result: IntentClassification,
        llm_result: IntentClassification
    ) -> IntentClassification:
        """Combine rule-based and LLM classifications."""
        # If they agree, boost confidence
        if rule_result.primary_intent == llm_result.primary_intent:
            return IntentClassification(
                primary_intent=rule_result.primary_intent,
                confidence=min(0.95, (rule_result.confidence + llm_result.confidence) / 2 + 0.1),
                secondary_intents=rule_result.secondary_intents,
                reasoning=f"Rule-based and LLM agree: {rule_result.primary_intent.value}"
            )

        # If they disagree, prefer LLM with reduced confidence
        return IntentClassification(
            primary_intent=llm_result.primary_intent,
            confidence=llm_result.confidence * 0.8,
            secondary_intents=[(rule_result.primary_intent, rule_result.confidence)],
            reasoning=f"LLM ({llm_result.primary_intent.value}) differs from rules ({rule_result.primary_intent.value})"
        )


def classify_intent(user_input: str, client: Optional[ClaudeClient] = None) -> CapabilityType:
    """
    Quick function to classify intent.

    Args:
        user_input: User's request
        client: Optional Claude client

    Returns:
        The classified CapabilityType
    """
    router = IntentRouter(client)
    result = router.classify(user_input)
    return result.primary_intent
