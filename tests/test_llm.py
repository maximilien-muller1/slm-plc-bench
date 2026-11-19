from slm_plc_bench.llm import complete                   # importe ta fonction depuis ton paquet

def test_complete_returns_text_and_tokens():             # pytest exécute toute fonction qui commence par test_
    result = complete(                                   # un vrai appel au modèle local
        "qwen2.5-coder:1.5b",                            # nom du modèle
        [{"role": "user", "content": "Say hello"}],      # un message court pour aller vite
    )
    assert result.text != ""                             # le modèle a bien répondu quelque chose
    assert result.prompt_tokens > 0                      # le serveur a compté les tokens lus
    assert result.completion_tokens > 0                  # et les tokens générés
    assert result.latency_s > 0                          # la durée est positive

import pytest                                              # pour tester qu'une erreur est bien levée
from slm_plc_bench.llm import throughput                   # la fonction à tester

def test_throughput_simple_case():                         # cas normal
    assert throughput(100, 2.0) == 50.0                    # 100 tokens en 2 s = 50 tokens/s

def test_throughput_rejects_zero_latency():                # cas limite
    with pytest.raises(ValueError):                        # on s'attend à une ValueError...
        throughput(100, 0.0)                               # ...quand la latence vaut 0