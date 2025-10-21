"""System Prompt Service for managing LLM system prompts and templates."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.database.models import SystemPrompt


# Default system prompt templates
DEFAULT_TEMPLATES = [
    {
        "name": "Customer Support Agent",
        "category": "customer_support",
        "prompt_text": """You are a helpful and professional customer support assistant for {company_name}.

Your responsibilities:
- Answer customer questions accurately and politely
- Help resolve customer issues efficiently
- Escalate complex problems to human agents when needed
- Maintain a friendly and empathetic tone

Guidelines:
- Keep responses concise and clear
- Ask clarifying questions when needed
- Never make promises you can't keep
- Always prioritize customer satisfaction

If you don't know the answer, admit it honestly and offer to connect the customer with a specialist.""",
        "variables": ["company_name"],
        "is_default": True,
        "is_template": True,
    },
    {
        "name": "Sales Assistant",
        "category": "sales",
        "prompt_text": """You are an enthusiastic and knowledgeable sales assistant for {company_name}.

Your goals:
- Understand customer needs and requirements
- Recommend appropriate products or services
- Highlight key benefits and features
- Answer questions about pricing and availability
- Guide customers through the purchase process

Sales approach:
- Be consultative, not pushy
- Listen actively to customer needs
- Provide honest recommendations
- Build trust and rapport
- Create value before closing

Always focus on solving the customer's problem rather than just making a sale.""",
        "variables": ["company_name"],
        "is_default": False,
        "is_template": True,
    },
    {
        "name": "Technical Support",
        "category": "technical",
        "prompt_text": """You are an expert technical support agent for {product_name} by {company_name}.

Your mission:
- Diagnose and troubleshoot technical issues
- Provide step-by-step solutions
- Explain technical concepts clearly
- Document known issues and workarounds

Support style:
- Be patient and understanding
- Avoid jargon unless necessary
- Provide detailed but clear instructions
- Verify the issue is resolved
- Offer preventive advice

If the issue requires escalation or is a known bug, inform the customer and provide expected resolution timeframe.""",
        "variables": ["product_name", "company_name"],
        "is_default": False,
        "is_template": True,
    },
    {
        "name": "Appointment Scheduler",
        "category": "scheduling",
        "prompt_text": """You are an efficient appointment scheduling assistant for {business_name}.

Your tasks:
- Help customers book, modify, or cancel appointments
- Check availability and suggest suitable time slots
- Collect necessary information (name, contact, service type)
- Confirm appointment details
- Send reminders and follow-ups

Scheduling guidelines:
- Always confirm date, time, and service type
- Ask about customer preferences
- Provide alternative options if requested slot is unavailable
- Be flexible and accommodating
- Verify contact information for reminders

Available slots: {available_hours}
Standard appointment duration: {appointment_duration}""",
        "variables": ["business_name", "available_hours", "appointment_duration"],
        "is_default": False,
        "is_template": True,
    },
    {
        "name": "General Assistant",
        "category": "general",
        "prompt_text": """You are a helpful, friendly, and intelligent AI assistant.

Your purpose:
- Assist users with a wide variety of questions and tasks
- Provide accurate and helpful information
- Engage in natural, conversational dialogue
- Admit when you don't know something

Communication style:
- Be clear and concise
- Use a warm and approachable tone
- Adapt to the user's communication style
- Ask follow-up questions when needed
- Provide examples to clarify concepts

Always prioritize being helpful while maintaining accuracy and honesty.""",
        "variables": [],
        "is_default": False,
        "is_template": True,
    },
]


class SystemPromptService:
    """Service for managing system prompts and templates."""

    def __init__(self, db: Session) -> None:
        """Initialize the service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_prompt(
        self,
        name: str,
        prompt_text: str,
        category: str,
        is_default: bool = False,
        is_template: bool = False,
        variables: Optional[List[str]] = None,
        meta_data: Optional[Dict] = None,
    ) -> SystemPrompt:
        """Create a new system prompt.

        Args:
            name: Prompt name
            prompt_text: Actual prompt text
            category: Category (customer_support, sales, etc.)
            is_default: Whether this is the default prompt
            is_template: Whether this is a built-in template
            variables: List of variable names in the prompt
            meta_data: Additional metadata

        Returns:
            Created SystemPrompt instance
        """
        # Auto-detect variables if not provided
        if variables is None:
            variables = self._extract_variables(prompt_text)

        # If this is the new default, unset other defaults
        if is_default:
            self._unset_defaults()

        prompt = SystemPrompt(
            name=name,
            prompt_text=prompt_text,
            category=category,
            is_default=is_default,
            is_template=is_template,
            variables=variables,
            meta_data=meta_data or {},
        )

        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)

        return prompt

    def get_prompt(self, prompt_id: str) -> Optional[SystemPrompt]:
        """Get a system prompt by ID.

        Args:
            prompt_id: Prompt identifier

        Returns:
            SystemPrompt or None if not found
        """
        return self.db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

    def list_prompts(
        self,
        category: Optional[str] = None,
        is_template: Optional[bool] = None,
    ) -> List[SystemPrompt]:
        """List system prompts with optional filters.

        Args:
            category: Filter by category
            is_template: Filter by template status

        Returns:
            List of SystemPrompt instances
        """
        query = self.db.query(SystemPrompt)

        if category:
            query = query.filter(SystemPrompt.category == category)

        if is_template is not None:
            query = query.filter(SystemPrompt.is_template == is_template)

        return query.order_by(SystemPrompt.created_at.desc()).all()

    def update_prompt(
        self,
        prompt_id: str,
        name: Optional[str] = None,
        prompt_text: Optional[str] = None,
        category: Optional[str] = None,
        is_default: Optional[bool] = None,
        variables: Optional[List[str]] = None,
        meta_data: Optional[Dict] = None,
    ) -> Optional[SystemPrompt]:
        """Update a system prompt.

        Args:
            prompt_id: Prompt identifier
            name: New name (optional)
            prompt_text: New prompt text (optional)
            category: New category (optional)
            is_default: New default status (optional)
            variables: New variables list (optional)
            meta_data: New metadata (optional)

        Returns:
            Updated SystemPrompt or None if not found
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None

        # Don't allow editing built-in templates
        if prompt.is_template:
            raise ValueError("Cannot edit built-in templates")

        # Update fields
        if name is not None:
            prompt.name = name
        if prompt_text is not None:
            prompt.prompt_text = prompt_text
            # Re-extract variables if text changed
            if variables is None:
                prompt.variables = self._extract_variables(prompt_text)
        if category is not None:
            prompt.category = category
        if is_default is not None:
            if is_default:
                self._unset_defaults()
            prompt.is_default = is_default
        if variables is not None:
            prompt.variables = variables
        if meta_data is not None:
            prompt.meta_data = meta_data

        self.db.commit()
        self.db.refresh(prompt)

        return prompt

    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a system prompt.

        Args:
            prompt_id: Prompt identifier

        Returns:
            True if deleted, False if not found
        """
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return False

        # Don't allow deleting built-in templates
        if prompt.is_template:
            raise ValueError("Cannot delete built-in templates")

        self.db.delete(prompt)
        self.db.commit()

        return True

    def get_default_prompt(self) -> Optional[SystemPrompt]:
        """Get the default system prompt.

        Returns:
            Default SystemPrompt or None if not set
        """
        return self.db.query(SystemPrompt).filter(SystemPrompt.is_default == True).first()

    def interpolate_variables(
        self,
        prompt_text: str,
        variables: Dict[str, str],
    ) -> str:
        """Replace variables in prompt text with actual values.

        Args:
            prompt_text: Prompt text with {variable} placeholders
            variables: Dict of variable name -> value mappings

        Returns:
            Interpolated prompt text
        """
        result = prompt_text
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            result = result.replace(placeholder, var_value)
        return result

    def _extract_variables(self, prompt_text: str) -> List[str]:
        """Extract variable names from prompt text.

        Args:
            prompt_text: Prompt text with {variable} placeholders

        Returns:
            List of variable names
        """
        # Find all {variable} patterns
        pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        matches = re.findall(pattern, prompt_text)
        return list(set(matches))  # Remove duplicates

    def _unset_defaults(self) -> None:
        """Unset all existing default prompts."""
        self.db.query(SystemPrompt).filter(SystemPrompt.is_default == True).update(
            {"is_default": False}
        )
        self.db.commit()

    def seed_default_templates(self) -> int:
        """Seed the database with default templates if not already present.

        Returns:
            Number of templates created
        """
        created = 0

        for template_data in DEFAULT_TEMPLATES:
            # Check if template already exists
            existing = (
                self.db.query(SystemPrompt)
                .filter(
                    SystemPrompt.name == template_data["name"],
                    SystemPrompt.is_template == True,
                )
                .first()
            )

            if not existing:
                self.create_prompt(**template_data)
                created += 1

        return created


__all__ = ["SystemPromptService", "DEFAULT_TEMPLATES"]
