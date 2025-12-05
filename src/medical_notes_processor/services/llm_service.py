"""
LLM service for medical note summarization.

This module provides a service layer for interacting with OpenAI's GPT models
to perform medical note summarization tasks. Uses LangChain for LLM orchestration.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, Any
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for LLM-powered medical note summarization.

    This service uses OpenAI's GPT models (via LangChain) to generate
    professional summaries of medical notes in SOAP format or similar.

    The service is configured to use temperature=0.0 for consistent,
    deterministic outputs suitable for medical documentation.

    Attributes:
        llm (ChatOpenAI): Configured LangChain ChatOpenAI instance
    """

    def __init__(self):
        """Initialize the LLM service with OpenAI configuration from settings."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.0,  # Deterministic for medical use
        )

    async def summarize_medical_note(self, text: str) -> Dict[str, Any]:
        """
        Summarize a medical note using GPT model.

        Generates a professional summary highlighting the key clinical information:
        - Patient's main complaint (chief complaint)
        - Key objective findings from examination
        - Diagnosis or assessment
        - Treatment plan and follow-up

        Uses a temperature of 0.0 for consistent, deterministic summaries.

        Args:
            text (str): Raw medical note text (typically in SOAP format)

        Returns:
            Dict[str, Any]: Dictionary containing:
                - summary (str): Generated summary text
                - model_used (str): Name of the model used (e.g., "gpt-4-turbo-preview")

        Raises:
            Exception: If the LLM API call fails

        Example:
            >>> service = LLMService()
            >>> result = await service.summarize_medical_note("SOAP Note - Patient presents with...")
            >>> print(result["summary"])
            "Patient presented with acute chest pain..."
        """
        system_prompt = """You are a medical documentation expert.
Summarize the following medical note concisely, highlighting:
- Patient's main complaint
- Key findings
- Diagnosis/Assessment
- Treatment plan

Keep the summary clear and professional."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=text)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            return {
                "summary": response.content,
                "model_used": settings.openai_model
            }
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            raise


# Global singleton instance for use throughout the application
llm_service = LLMService()
