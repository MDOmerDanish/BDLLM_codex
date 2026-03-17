from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ProviderStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


@dataclass
class Provider:
    provider_id: str
    model_name: str
    token_price: float
    hardware_tps: int
    expected_quality: float
    reputation: float = 0.5
    status: ProviderStatus = ProviderStatus.PENDING


@dataclass
class RegistrationRequest:
    provider: Provider


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ServiceSession:
    session_id: str
    user_id: str
    provider_id: str
    prompt: str
    response: str = ""
    token_count: int = 0
    signed_states: List[str] = field(default_factory=list)


class ChannelState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    DISPUTED = "disputed"


@dataclass
class PaymentChannel:
    channel_id: str
    user_id: str
    provider_id: str
    user_deposit: float
    provider_deposit: float
    user_balance: float
    provider_balance: float
    nonce: int = 0
    state: ChannelState = ChannelState.OPEN


class DisputeVerdict(str, Enum):
    USER_WINS = "user_wins"
    PROVIDER_WINS = "provider_wins"


@dataclass
class DisputeResult:
    session_id: str
    verdict: DisputeVerdict
    quality_score: float
    min_quality: float
    reason: str


@dataclass
class LedgerEntry:
    provider_id: str
    token_price: float
    reputation: float
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class SettlementResult:
    channel_id: str
    user_payout: float
    provider_payout: float
    settled_nonce: int
