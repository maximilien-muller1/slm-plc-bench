# Étape 1 — Mesures de vitesse

## Configuration
- Machine : MacBook Pro M4 Max, 64 Go
- Bande passante mémoire : 546 Go/s (chiffre annoncé, à vérifier sur la fiche Apple)
- Moteur : Ollama (servi par brew services)
- Modèles : qwen2.5-coder:1.5b (0,99 Go) et qwen2.5-coder:7b (4,7 Go), quantification par défaut d'Ollama
- Température : 0
- Protocole script : 1 appel de préchauffage ignoré, puis 5 prompts × 3 répétitions = 15 mesures par modèle
- Débit script = tokens générés / latence totale de l'appel

## Prédiction (écrite AVANT la mesure)
- Débit théorique max = bande passante / taille du modèle
  - 1.5B : 546 / 0,99 ≈ 550 tokens/s
  - 7B : 546 / 4,7 ≈ 116 tokens/s
- Le 7B devrait être environ 4,7 fois plus lent (la bande passante disparaît du rapport : 4,7 / 0,99)

## Résultats

| | 1.5B | 7B | Rapport 1.5B / 7B |
| --- | --- | --- | --- |
| Script : débit médian (min / max) | 200,6 (191 / 216) | 55,4 (46 / 77) | 3,6 |
| Ollama --verbose : génération pure (eval rate) | 210 tokens/s | 86 tokens/s | 2,4 |
| Plafond théorique | 550 | 116 | 4,7 |
| Part du plafond atteinte (eval rate) | 38 % | 74 % | |
| Ollama --verbose : prefill (prompt eval rate) | 916 tokens/s | 206 tokens/s | 4,4 |
| Chargement du modèle (load duration) | 0,55 s | 0,78 s | |

## Analyse

### 1. La règle « bande passante / taille » marche pour le gros modèle, pas pour le petit
- Le 7B atteint 74 % du plafond : conforme à la pratique (on n'atteint jamais 100 % de la bande passante).
- Le 1.5B n'atteint que 38 % : il génère si vite que d'autres coûts dominent
  (lancement des calculs couche par couche, tirage du token parmi ~150 000, travail côté processeur).
  Ces coûts ne diminuent pas avec la taille du modèle.
- Conséquence : un petit modèle n'est pas purement limité par la mémoire. Le quantifier davantage
  l'accélérera moins que prévu (à vérifier à l'étape 8).

### 2. Le prefill confirme la théorie
- Rapport de prefill 4,4, proche du rapport de taille 4,7.
- Normal : le prefill est limité par le calcul, proportionnel au nombre de paramètres,
  alors que la génération est limitée par la mémoire (plus les surcoûts fixes).

### 3. Le débit mesuré par le script sous-estime le vrai débit
- La latence totale contient, en plus de la génération : le prefill, le trajet HTTP,
  la préparation de la requête.
- Ce temps fixe pèse plus sur les réponses courtes (réparti sur moins de tokens),
  ce qui explique une partie de la variabilité, surtout pour le 7B.
- Bruit supplémentaire : autres applis en arrière-plan, gestion d'énergie (batterie, température).

### Question ouverte
- Pour le 1.5B, le script est fiable (201 contre 210). Pour le 7B, non (55 contre 86).
- Le prefill (~0,2 s) et le HTTP ne suffisent pas à expliquer un tel écart.
- Hypothèses : modèle déchargé puis rechargé pendant la série, ou pression mémoire.
- À vérifier : relancer le script avec le 7B seul, en surveillant `ollama ps` dans un autre terminal.

## Observations sur la qualité du code généré (prompt : compteur de pièces)
- 7B : contexte automate compris, mais il compte à chaque cycle tant que l'entrée est vraie
  (il fallait détecter le front montant avec R_TRIG). Utilise METHOD et ajoute un PROGRAM.
  543 tokens dont plus de la moitié d'explications (~3 s perdues).
- 1.5B : ce n'est pas du Structured Text valide (PARAMETERS, BEGIN, FOR ... IN, ARRAY OF STRING)
  et la tâche est mal comprise (compte les éléments d'une liste, pas des pièces devant un capteur).
- Question du projet : le 1.5B est 2,4 fois plus rapide, mais combien de ses réponses sont utilisables ?

## Questions de compréhension
1. Le gros modèle est-il environ 4,7 fois plus lent ?
   Non : 2,4 fois en génération pure. Le petit modèle est freiné par des surcoûts fixes qui ne
   dépendent pas de sa taille (voir analyse 1).
2. Pourquoi le premier appel est-il plus lent ?
   Le modèle doit être chargé du disque en mémoire (0,55 à 0,78 s mesurés). Ollama le décharge
   après ~5 min d'inactivité. D'où l'appel de préchauffage ignoré.
3. Pourquoi le temps jusqu'au premier token augmente-t-il avec la longueur du prompt ?
   À vérifier en 1.3. Hypothèse : le prefill doit traiter tout le prompt avant de générer
   le premier token.
4. Pourquoi « tokens / latence totale » sous-estime-t-il le vrai débit ?
   La latence totale inclut le prefill, le HTTP et la préparation, en plus de la génération.
5. À température 0, les réponses sont-elles strictement identiques ?
   À vérifier en 1.3.

## Médiane plutôt que moyenne
La médiane n'est presque pas affectée par une mesure aberrante (par exemple une mesure ralentie
par une tâche de fond), alors qu'une seule valeur extrême peut fausser la moyenne.