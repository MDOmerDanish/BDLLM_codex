from bdllm import BDLLMSystem, Provider
from bdllm.models import DisputeVerdict, ProviderStatus


def test_registration_success_and_ledger_discovery():
    system = BDLLMSystem()
    provider = Provider(
        provider_id="p1",
        model_name="llama3-8b",
        token_price=0.02,
        hardware_tps=25,
        expected_quality=0.8,
        reputation=0.9,
    )

    assert system.registration_request(provider) is True
    assert provider.status == ProviderStatus.VERIFIED

    offers = system.ledger.fetch_model(max_token_price=0.03, min_reputation=0.5)
    assert len(offers) == 1
    assert offers[0].provider_id == "p1"


def test_registration_rejected_when_hardware_too_low():
    system = BDLLMSystem()
    provider = Provider(
        provider_id="weak-node",
        model_name="llama3-8b",
        token_price=0.01,
        hardware_tps=5,
        expected_quality=0.8,
    )

    assert system.registration_request(provider) is False
    assert provider.status == ProviderStatus.REJECTED


def test_end_to_end_session_and_settlement():
    system = BDLLMSystem()
    provider = Provider(
        provider_id="p2",
        model_name="llama3-8b",
        token_price=0.01,
        hardware_tps=30,
        expected_quality=0.9,
    )
    system.registration_request(provider)

    result = system.run_session(
        user_id="bob",
        provider_id="p2",
        prompt="Describe architecture of decentralized model inference with payment channels and dispute resolution.",
        price_cap=0.03,
    )

    assert result["settlement"]["settled_nonce"] == 1
    assert result["settlement"]["provider_payout"] > 5.0
    assert result["dispute"]["verdict"] in {DisputeVerdict.PROVIDER_WINS.value, DisputeVerdict.USER_WINS.value}
