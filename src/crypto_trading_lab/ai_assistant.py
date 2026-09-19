"""AI research assistant (ROADMAP.md chapter 55).

Provides AI-assisted research capabilities for strategy development
and hypothesis generation. This is a research-tier capability.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class AssistantRole(Enum):
    """AI assistant role."""
    HYPOTHESIS_GENERATOR = "hypothesis_generator"
    CODE_REVIEWER = "code_reviewer"
    DATA_ANALYST = "data_analyst"
    STRATEGY_CRITIC = "strategy_critic"
    DOCUMENTATION = "documentation"


@dataclass
class AssistantMessage:
    """A message in the AI conversation."""
    message_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


@dataclass
class AIConversation:
    """Conversation with AI assistant."""
    conversation_id: str
    role: AssistantRole
    created_at: datetime
    updated_at: datetime
    messages: list[AssistantMessage] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: dict | None = None) -> AssistantMessage:
        """Add a message to the conversation."""
        message = AssistantMessage(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        return message
    
    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [
                {
                    "message_id": m.message_id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in self.messages
            ],
            "context": self.context,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AIConversation":
        conv = cls(
            conversation_id=data["conversation_id"],
            role=AssistantRole(data["role"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            context=data.get("context", {}),
        )
        for msg_data in data.get("messages", []):
            msg = AssistantMessage(
                message_id=msg_data["message_id"],
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                metadata=msg_data.get("metadata", {}),
            )
            conv.messages.append(msg)
        return conv


class AIAssistant:
    """
    AI research assistant for strategy development (55.1).
    
    Provides AI-assisted research capabilities for strategy development
    and hypothesis generation. This is a research-tier capability.
    """
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._conversations: dict[str, AIConversation] = {}
    
    def create_conversation(self, role: AssistantRole, context: dict | None = None) -> AIConversation:
        """Create a new AI conversation with specified role."""
        conv = AIConversation(
            conversation_id=str(uuid.uuid4()),
            role=role,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            context=context or {},
        )
        # Add system prompt based on role
        system_prompt = self._get_system_prompt(role)
        conv.add_message("system", system_prompt, {"role": role.value})
        self._conversations[conv.conversation_id] = conv
        self._save(conv)
        return conv
    
    def _get_system_prompt(self, role: AssistantRole) -> str:
        """Get system prompt for the given role."""
        prompts = {
            AssistantRole.HYPOTHESIS_GENERATOR: (
                "You are a financial research hypothesis generator. "
                "Generate testable, falsifiable trading hypotheses based on "
                "market observations, academic literature, and quantitative principles. "
                "Always include: 1) Clear hypothesis statement, 2) Null hypothesis, "
                "3) Test methodology, 4) Expected effect size, 5) Required sample size, "
                "6) Potential confounds, 7) Pre-registration template."
            ),
            AssistantRole.CODE_REVIEWER: (
                "You are a quantitative code reviewer. "
                "Review trading strategy code for: 1) Look-ahead bias, "
                "2) Survivorship bias, 3) Overfitting signs, 3) Data leakage, "
                "4) Correct execution model (next-open fill), "
                "5) Proper cost modeling, 6) Statistical validity of backtests."
            ),
            AssistantRole.DATA_ANALYST: (
                "You are a financial data analyst. "
                "Analyze market data for: 1) Stationarity, 2) Autocorrelation, "
                "3) Regime changes, 4) Structural breaks, 5) Outlier detection, "
                "6) Feature importance, 7) Data quality issues."
            ),
            AssistantRole.STRATEGY_CRITIC: (
                "You are a strategy critic. "
                "Critique trading strategies for: 1) Overfitting risk, "
                "2) Selection bias, 3) Transaction cost sensitivity, "
                "4) Regime dependency, 5) Capacity limits, "
                "6) Operational feasibility, 7) Comparison to appropriate benchmarks."
            ),
            AssistantRole.DOCUMENTATION: (
                "You are a research documentation specialist. "
                "Create clear, reproducible documentation for: "
                "1) Experiment design, 2) Methodology, 3) Results, "
                "4) Limitations, 5) Reproducibility instructions."
            ),
        }
        return prompts.get(role, "You are a research assistant.")
    
    def get_conversation(self, conversation_id: str) -> AIConversation | None:
        """Get conversation by ID."""
        if conversation_id not in self._conversations:
            self._load(conversation_id)
        return self._conversations.get(conversation_id)
    
    def add_message(self, conversation_id: str, role: str, content: str) -> AssistantMessage | None:
        """Add a message to a conversation."""
        conv = self.get_conversation(conversation_id)
        if not conv:
            return None
        return conv.add_message(role, content)
    
    def get_conversation_history(self, conversation_id: str) -> list[dict]:
        """Get conversation history as list of dicts."""
        conv = self.get_conversation(conversation_id)
        if not conv:
            return []
        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in conv.messages
        ]
    
    def _save(self, conv: AIConversation) -> None:
        path = self.storage_path / f"{conv.conversation_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conv.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _load(self, conversation_id: str) -> AIConversation | None:
        path = self.storage_path / f"{conversation_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        conv = AIConversation.from_dict(data)
        self._conversations[conversation_id] = conv
        return conv


AI_ASSISTANT_WARNING = (
    "AI assistant outputs are research suggestions only. "
    "All outputs must be independently validated. "
    "Never execute trades based solely on AI suggestions. "
    "AI can hallucinate, confabulate, and confidently state falsehoods. "
    "Always verify independently before any trading decision."
)


__all__ = [
    "AssistantRole",
    "AssistantMessage",
    "AIConversation",
    "AIAssistant",
    "AI_ASSISTANT_WARNING",
]
