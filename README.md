<<<<<<< ours
# BDLLM Project

This project is a demonstration of the BDLLM project.
=======
# BDLLM Prototype

This repository now contains a runnable prototype of the BDLLM system described in the IEEE draft:

- Provider registration + validator checks (`verify_power`, `verify_model`)
- On-ledger discovery (`fetch_model`)
- Off-chain payment channels for token-level settlement
- Inference service exchange simulation
- LLM-as-a-Judge inspired dispute resolution

## Quickstart

```bash
python main.py
pytest
```

## Structure

- `bdllm/models.py` – Core domain models.
- `bdllm/services.py` – Registration, ledger, channels, service exchange, dispute resolver, and top-level system orchestrator.
- `main.py` – End-to-end demo scenario.
- `tests/test_bdllm.py` – Basic regression tests.
>>>>>>> theirs
