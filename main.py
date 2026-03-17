from pprint import pprint

from bdllm import BDLLMSystem, Provider


def demo() -> None:
    system = BDLLMSystem()

    provider = Provider(
        provider_id="node-001",
        model_name="llama3-8b",
        token_price=0.03,
        hardware_tps=42,
        expected_quality=0.84,
        reputation=0.91,
    )

    approved = system.registration_request(provider)
    if not approved:
        print("Provider failed validator checks")
        return

    result = system.run_session(
        user_id="alice",
        provider_id="node-001",
        prompt="Explain why off-chain payment channels improve latency in decentralized LLM serving.",
        price_cap=0.05,
    )

    pprint(result)


if __name__ == "__main__":
    demo()
