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
