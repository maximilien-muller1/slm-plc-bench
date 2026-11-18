import statistics                                      # médiane, min, max d'une liste de nombres
from slm_plc_bench.llm import complete                 # ton client de l'étape 1.1

MODELS = ["qwen2.5-coder:1.5b", "qwen2.5-coder:7b"]    # les deux modèles à comparer
PROMPTS = [                                            # 5 demandes de code automate différentes
    "Write a Structured Text FUNCTION_BLOCK that starts a motor with a start button and stops it with a stop button.",
    "Write a Structured Text FUNCTION_BLOCK that turns a lamp on for 5 seconds after a button press, using a TON timer.",
    "Write a Structured Text FUNCTION_BLOCK that counts parts passing in front of a sensor.",
    "Write a Structured Text FUNCTION_BLOCK that fills a tank between a low and a high level sensor.",
    "Write a Structured Text FUNCTION_BLOCK that makes a warning lamp blink every 500 ms.",
]
REPEATS = 3                                            # chaque prompt est envoyé 3 fois

def measure(model: str) -> list[float]:
    complete(model, [{"role": "user", "content": "Say hello"}])   # préchauffage : charge le modèle, mesure ignorée
    speeds = []                                        # liste des débits mesurés, en tokens par seconde
    for prompt in PROMPTS:                             # pour chaque prompt...
        for _ in range(REPEATS):                       # ...répété REPEATS fois (_ = variable dont on ne se sert pas)
            result = complete(model, [{"role": "user", "content": prompt}])  # un appel mesuré
            speeds.append(result.completion_tokens / result.latency_s)   # débit de cet appel, ajouté à la liste
    return speeds                                      # 15 mesures par modèle

if __name__ == "__main__":                             # ce bloc ne s'exécute que si on lance le fichier directement
    for model in MODELS:                               # pour chaque modèle...
        speeds = measure(model)                        # ...on fait les 15 mesures
        print(f"{model}: médiane {statistics.median(speeds):.1f} tokens/s "   # médiane, arrondie à 1 décimale
              f"(min {min(speeds):.1f}, max {max(speeds):.1f})")              # min et max de la même liste