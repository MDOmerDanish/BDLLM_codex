from __future__ import annotations

import hashlib
import math
import random
import uuid
from dataclasses import asdict
from typing import Dict, Iterable, List

from .models import (
    ChannelState,
    DisputeResult,
    DisputeVerdict,
    LedgerEntry,
    PaymentChannel,
    Provider,
    ProviderStatus,
    RegistrationRequest,
    ServiceSession,
    SettlementResult,
)


class ValidatorNetwork:
    """Permissioned validator set that verifies provider quality and capacity."""

    def __init__(self, min_tps: int = 20, min_quality: float = 0.65) -> None:
        self.min_tps = min_tps
        self.min_quality = min_quality

    def verify_power(self, provider: Provider) -> bool:
        return provider.hardware_tps >= self.min_tps

    def verify_model(self, provider: Provider) -> bool:
        return provider.expected_quality >= self.min_quality

    def evaluate_registration(self, req: RegistrationRequest) -> bool:
        provider = req.provider
        ok = self.verify_power(provider) and self.verify_model(provider)
        provider.status = ProviderStatus.VERIFIED if ok else ProviderStatus.REJECTED
        return ok


class PublicBlockchainLedger:
    """In-memory registry emulating blockchain world-state entries."""

    def __init__(self) -> None:
        self._entries: Dict[str, LedgerEntry] = {}

    def add_provider(self, provider: Provider) -> None:
        if provider.status != ProviderStatus.VERIFIED:
            raise ValueError("Only verified providers may be recorded")
        self._entries[provider.provider_id] = LedgerEntry(
            provider_id=provider.provider_id,
            token_price=provider.token_price,
            reputation=provider.reputation,
            metadata={"model": provider.model_name, "status": provider.status.value},
        )

    def fetch_model(self, max_token_price: float, min_reputation: float = 0.0) -> List[LedgerEntry]:
        results = [
            e
            for e in self._entries.values()
            if e.token_price <= max_token_price and e.reputation >= min_reputation
        ]
        return sorted(results, key=lambda e: (e.token_price, -e.reputation))


class InferenceEngine:
    """vLLM-like abstraction. Here we simulate token streaming deterministically."""

    @staticmethod
    def generate(prompt: str, model_name: str) -> str:
        summary = f"[{model_name}] "
        if len(prompt) < 20:
            return summary + "Please provide more context to generate a robust answer."
        return summary + "Response: " + " ".join(prompt.split()[:40])


class PaymentChannelManager:
    def __init__(self) -> None:
        self.channels: Dict[str, PaymentChannel] = {}

    def open_channel(self, user_id: str, provider_id: str, user_deposit: float, provider_deposit: float) -> PaymentChannel:
        channel_id = str(uuid.uuid4())
        channel = PaymentChannel(
            channel_id=channel_id,
            user_id=user_id,
            provider_id=provider_id,
            user_deposit=user_deposit,
            provider_deposit=provider_deposit,
            user_balance=user_deposit,
            provider_balance=provider_deposit,
        )
        self.channels[channel_id] = channel
        return channel

    def update_state(self, channel_id: str, token_count: int, token_price: float) -> str:
        channel = self.channels[channel_id]
        if channel.state != ChannelState.OPEN:
            raise ValueError("Channel must be open to update state")

        charge = token_count * token_price
        if charge > channel.user_balance:
            raise ValueError("Insufficient user balance")

        channel.user_balance -= charge
        channel.provider_balance += charge
        channel.nonce += 1

        payload = f"{channel.channel_id}:{channel.nonce}:{channel.user_balance:.8f}:{channel.provider_balance:.8f}"
        signature = hashlib.sha256(payload.encode()).hexdigest()
        return signature

    def close_channel(self, channel_id: str) -> SettlementResult:
        channel = self.channels[channel_id]
        channel.state = ChannelState.CLOSED
        return SettlementResult(
            channel_id=channel.channel_id,
            user_payout=channel.user_balance,
            provider_payout=channel.provider_balance,
            settled_nonce=channel.nonce,
        )


class ServiceExchange:
    def __init__(self, inference_engine: InferenceEngine, channels: PaymentChannelManager) -> None:
        self.inference_engine = inference_engine
        self.channels = channels
        self.sessions: Dict[str, ServiceSession] = {}

    def service_exchange(self, channel_id: str, user_id: str, provider_id: str, prompt: str, token_price: float) -> ServiceSession:
        response = self.inference_engine.generate(prompt, "llama3-8b")
        token_count = max(1, math.ceil(len(response.split()) * 1.2))

        signature = self.channels.update_state(channel_id, token_count, token_price)
        session = ServiceSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            provider_id=provider_id,
            prompt=prompt,
            response=response,
            token_count=token_count,
            signed_states=[signature],
        )
        self.sessions[session.session_id] = session
        return session


class JudgeModel:
    """Simple LLM-as-a-Judge inspired scorer with safety and quality checks."""

    BAD_PATTERNS = {"asdf", "lorem", "blah", "gibberish"}

    def score(self, prompt: str, response: str) -> float:
        p_words = set(w.strip(".,!?").lower() for w in prompt.split() if len(w) > 3)
        r_words = [w.strip(".,!?").lower() for w in response.split()]
        if not r_words:
            return 0.0

        overlap = sum(1 for w in r_words if w in p_words) / len(r_words)
        badness = sum(1 for w in r_words if w in self.BAD_PATTERNS) / len(r_words)
        length_bonus = min(len(r_words) / 40.0, 1.0) * 0.2
        score = max(0.0, min(1.0, overlap * 0.9 + length_bonus - badness))
        return score


class DisputeResolver:
    def __init__(self, judge: JudgeModel, min_quality: float = 0.35) -> None:
        self.judge = judge
        self.min_quality = min_quality

    def dispute_resolve(self, session: ServiceSession) -> DisputeResult:
        quality_score = self.judge.score(session.prompt, session.response)
        if quality_score < self.min_quality:
            verdict = DisputeVerdict.USER_WINS
            reason = "Generated response failed minimum quality threshold"
        else:
            verdict = DisputeVerdict.PROVIDER_WINS
            reason = "Generated response passed minimum quality threshold"

        return DisputeResult(
            session_id=session.session_id,
            verdict=verdict,
            quality_score=quality_score,
            min_quality=self.min_quality,
            reason=reason,
        )




def _serialize(value):
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value

class BDLLMSystem:
    def __init__(self) -> None:
        self.validators = ValidatorNetwork()
        self.ledger = PublicBlockchainLedger()
        self.channels = PaymentChannelManager()
        self.exchange = ServiceExchange(InferenceEngine(), self.channels)
        self.disputes = DisputeResolver(JudgeModel())

    def registration_request(self, provider: Provider) -> bool:
        req = RegistrationRequest(provider=provider)
        approved = self.validators.evaluate_registration(req)
        if approved:
            self.ledger.add_provider(provider)
        return approved

    def run_session(self, user_id: str, provider_id: str, prompt: str, price_cap: float) -> dict:
        offers = self.ledger.fetch_model(max_token_price=price_cap)
        offer = next((o for o in offers if o.provider_id == provider_id), None)
        if not offer:
            raise ValueError("Provider not available under current budget")

        channel = self.channels.open_channel(user_id, provider_id, user_deposit=20.0, provider_deposit=5.0)
        session = self.exchange.service_exchange(channel.channel_id, user_id, provider_id, prompt, offer.token_price)
        dispute = self.disputes.dispute_resolve(session)

        if dispute.verdict == DisputeVerdict.USER_WINS:
            channel.state = ChannelState.DISPUTED
        settlement = self.channels.close_channel(channel.channel_id)

        return {
            "channel": _serialize(asdict(channel)),
            "session": _serialize(asdict(session)),
            "dispute": _serialize(asdict(dispute)),
            "settlement": _serialize(asdict(settlement)),
        }
