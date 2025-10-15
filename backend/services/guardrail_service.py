"""Three-layer guardrail system for content safety and policy compliance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from backend.database import SessionLocal
from backend.database.repositories import GuardrailRepository
from backend.utils.logging import get_logger


@dataclass
class GuardrailViolation:
    """Represents a detected guardrail violation."""

    layer: str  # "pre_llm", "llm_prompt", "post_llm"
    rule_type: str
    severity: str  # "low", "medium", "high"
    message: str
    blocked: bool


@dataclass
class GuardrailResult:
    """Result of guardrail check."""

    passed: bool
    violations: List[GuardrailViolation]
    safe_response: Optional[str] = None  # Fallback response if blocked


class GuardrailService:
    """
    Three-layer guardrail system:
    Layer 1: Pre-LLM (Fast keyword/pattern checks)
    Layer 2: LLM Prompt (Instructions in system prompt)
    Layer 3: Post-LLM (Response validation)
    """

    # Layer 1: Pre-LLM blocked keywords
    BLOCKED_KEYWORDS = [
        # Medical advice
        "medical advice",
        "prescribe medication",
        "diagnose disease",
        "treatment for",
        "cure for cancer",
        # Legal advice
        "legal advice",
        "sue someone",
        "write a contract",
        "legal representation",
        # Financial advice
        "financial advice",
        "invest my money",
        "stock tips",
        "crypto investment",
        # Harmful content
        "how to make bomb",
        "how to make weapon",
        "illegal drugs",
        "hack into",
        # Personal information requests
        "credit card number",
        "social security number",
        "bank account details",
    ]

    # PII patterns for Layer 3
    PII_PATTERNS = {
        "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    }

    def __init__(self, enabled: bool = True, enable_db_logging: bool = True):
        """
        Initialize guardrail service.

        Args:
            enabled: Whether guardrails are enabled
            enable_db_logging: Whether to log violations to database
        """
        self.enabled = enabled
        self.enable_db_logging = enable_db_logging
        self.logger = get_logger(__name__)

    def check_input(self, user_input: str) -> GuardrailResult:
        """
        Layer 1: Pre-LLM fast checks on user input.

        Args:
            user_input: User's input text

        Returns:
            GuardrailResult indicating if input is safe
        """
        if not self.enabled:
            return GuardrailResult(passed=True, violations=[])

        violations = []
        user_input_lower = user_input.lower()

        # Check for blocked keywords
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in user_input_lower:
                violations.append(
                    GuardrailViolation(
                        layer="pre_llm",
                        rule_type="blocked_keyword",
                        severity="high",
                        message=f"Input contains blocked keyword: {keyword}",
                        blocked=True,
                    )
                )

        if violations:
            return GuardrailResult(
                passed=False,
                violations=violations,
                safe_response="I'm here to help with questions about our products and services. "
                "I'm not able to provide medical, legal, or financial advice, "
                "or assist with harmful requests.",
            )

        return GuardrailResult(passed=True, violations=[])

    def get_system_prompt_guardrails(self) -> str:
        """
        Layer 2: Get guardrail instructions for LLM system prompt.

        Returns:
            Guardrail instructions to include in system prompt
        """
        if not self.enabled:
            return ""

        return """
STRICT GUARDRAILS - YOU MUST FOLLOW THESE RULES:

1. SCOPE LIMITATION:
   - ONLY answer questions about our products, services, and company information
   - Politely decline questions outside this scope

2. PROHIBITED CONTENT:
   - NEVER provide medical, legal, or financial advice
   - NEVER generate harmful, dangerous, or illegal content
   - NEVER provide instructions for weapons, drugs, or illegal activities
   - NEVER assist with hacking, fraud, or other illegal activities

3. PRIVACY PROTECTION:
   - NEVER generate, request, or share Personal Identifiable Information (PII)
   - NEVER share credit card numbers, SSNs, passwords, or account details
   - NEVER create fake identities or credentials

4. RESPONSE GUIDELINES:
   - Keep responses concise (under 100 words for voice)
   - Be professional, helpful, and respectful
   - If you don't know something, say so - don't make up information
   - If asked something prohibited, politely explain what you CAN help with

If a request violates these guardrails, respond with:
"I'm here to help with questions about our products and services. I'm not able to assist with [specific request type].
Is there something else I can help you with?"
"""

    def check_output(self, llm_response: str) -> GuardrailResult:
        """
        Layer 3: Post-LLM validation of generated response.

        Args:
            llm_response: The LLM's generated response

        Returns:
            GuardrailResult indicating if response is safe
        """
        if not self.enabled:
            return GuardrailResult(passed=True, violations=[])

        violations = []

        # Check for PII leakage
        for pii_type, pattern in self.PII_PATTERNS.items():
            if pattern.search(llm_response):
                violations.append(
                    GuardrailViolation(
                        layer="post_llm",
                        rule_type="pii_detected",
                        severity="high",
                        message=f"Response contains {pii_type}",
                        blocked=True,
                    )
                )

        # Check response length (for voice, should be reasonable)
        word_count = len(llm_response.split())
        if word_count > 150:
            violations.append(
                GuardrailViolation(
                    layer="post_llm",
                    rule_type="response_too_long",
                    severity="medium",
                    message=f"Response is {word_count} words (max 150)",
                    blocked=True,
                )
            )

        # Check for blocked keywords in response (shouldn't generate prohibited content)
        response_lower = llm_response.lower()
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in response_lower:
                violations.append(
                    GuardrailViolation(
                        layer="post_llm",
                        rule_type="prohibited_content",
                        severity="high",
                        message=f"Response contains prohibited content: {keyword}",
                        blocked=True,
                    )
                )

        if violations:
            return GuardrailResult(
                passed=False,
                violations=violations,
                safe_response="I apologize, but I cannot provide that information. "
                "Is there something else about our products or services I can help you with?",
            )

        return GuardrailResult(passed=True, violations=[])

    def log_violation(self, violation: GuardrailViolation, context: dict) -> None:
        """
        Log a guardrail violation for monitoring and improvement.

        Args:
            violation: The detected violation
            context: Additional context (session_id, turn_id, input_text, output_text, etc.)
        """
        # Log to console for immediate visibility
        self.logger.warning(
            f"Guardrail violation detected: {violation.layer} - {violation.rule_type}",
            extra={
                "violation": {
                    "layer": violation.layer,
                    "rule_type": violation.rule_type,
                    "severity": violation.severity,
                    "message": violation.message,
                    "blocked": violation.blocked,
                },
                "context": context,
            },
        )

        # Persist to database if enabled
        if self.enable_db_logging:
            try:
                with SessionLocal() as db:
                    guardrail_repo = GuardrailRepository(db)

                    # Map layer string to layer number
                    layer_map = {"pre_llm": 1, "llm_prompt": 2, "post_llm": 3}
                    layer_num = layer_map.get(violation.layer, 0)

                    guardrail_repo.log_violation(
                        violation_type=violation.rule_type,
                        layer=layer_num,
                        violated_rule=violation.message,
                        session_id=context.get("session_id"),
                        turn_id=context.get("turn_id"),
                        severity=violation.severity,
                        input_text=context.get("input_text"),
                        output_text=context.get("output_text"),
                        safe_response=context.get("safe_response"),
                        metadata={
                            "blocked": violation.blocked,
                            "layer_name": violation.layer,
                            **{k: v for k, v in context.items() if k not in ["session_id", "turn_id", "input_text", "output_text", "safe_response"]},
                        },
                    )

                    self.logger.debug(
                        "Guardrail violation logged to database",
                        extra={"session_id": context.get("session_id"), "turn_id": context.get("turn_id")},
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to log guardrail violation to database: {e}",
                    extra={"error": str(e), "session_id": context.get("session_id")},
                )


__all__ = ["GuardrailService", "GuardrailResult", "GuardrailViolation"]
