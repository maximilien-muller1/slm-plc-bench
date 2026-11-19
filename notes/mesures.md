# Étape 1 — Mesures de vitesse
 
## Configuration
- Machine : MacBook Pro M4 Max, 64 Go (Mac16,6)
- Bande passante mémoire : 546 Go/s (chiffre annoncé, à vérifier sur la fiche Apple)
- Alimentation : secteur
- Moteur : Ollama (servi par brew services)
- Modèles : qwen2.5-coder:1.5b (0,99 Go) et qwen2.5-coder:7b (4,7 Go), quantification par défaut d'Ollama
- Température : 0
- Protocole script : 1 appel de préchauffage ignoré, puis 5 prompts × 3 répétitions = 15 mesures par modèle
- Pause de 10 s entre les appels pour les mesures de débit (voir « Question résolue »)
- Débit script = tokens générés / latence totale de l'appel
## Prédiction (écrite AVANT la mesure)
- Débit théorique max = bande passante / taille du modèle
  - 1.5B : 546 / 0,99 ≈ 550 tokens/s
  - 7B : 546 / 4,7 ≈ 116 tokens/s
- Le 7B devrait être environ 4,7 fois plus lent (la bande passante disparaît du rapport : 4,7 / 0,99)
## Résultats
 
| | 1.5B | 7B | Rapport 1.5B / 7B |
| --- | --- | --- | --- |
| Script sans pause : débit médian (min / max) | 200,6 (191 / 216) | 55,4 (46 / 77) | 3,6 |
| Script avec pause de 10 s : débit médian (min / max) | non mesuré | 80,7 (53 / 85) | |
| Ollama --verbose : génération pure (eval rate) | 210 tokens/s | 86 tokens/s | 2,4 |
| Plafond théorique | 550 | 116 | 4,7 |
| Part du plafond atteinte (eval rate) | 38 % | 74 % | |
| Ollama --verbose : prefill (prompt eval rate), prompt de 40 tokens | 916 tokens/s | 206 tokens/s | 4,4 |
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
- Première hypothèse : un temps fixe par appel (prefill, HTTP). Réfutée pour le 7B :
  les réponses sont trop longues pour qu'il pèse (voir « Question résolue »).
- Cause principale pour le 7B : le bridage de puissance en charge continue.
- Le temps fixe reste réel mais faible : il explique le petit écart du 1.5B (201 contre 210).
- Bruit supplémentaire : autres applis en arrière-plan.
### Question résolue : pourquoi le script mesurait 55 tokens/s pour le 7B, contre 86 avec Ollama
 
**Hypothèses écartées**
- Temps fixe par appel (prefill, HTTP) : les réponses font 525 à 839 tokens, donc un temps fixe
  de quelques dixièmes de seconde serait négligeable. La régression latence = a + tokens / débit
  donne des valeurs absurdes (a = 3,8 s, ou négatif sans le premier prompt) : le bruit est plus
  grand que l'effet, le modèle « temps fixe + débit constant » est faux.
- Modèle en partie sur le processeur : `ollama ps` affiche 100% GPU.
- Batterie : 55,4 tokens/s branché, 56,2 sur batterie, aucune différence.
**Indice décisif** : l'ordre des appels. Le 1er appel tourne à 80 tokens/s, les suivants à 54-62.
Le même prompt ralentit à chaque répétition (839 tokens en 10,4 puis 12,6 puis 13,4 s).
 
**Hypothèse confirmée : bridage de puissance en charge continue**
 
Log GPU (`sudo powermetrics --samplers gpu_power -i 1000`) pendant 3 appels :
 
| Moment de l'appel | Appel 1 | Appel 2 | Appel 3 |
| --- | --- | --- | --- |
| Premières secondes | 1 578 MHz, 44 W | 1 578 MHz, 44 W | 1 578 MHz, 44 W |
| Fin de l'appel | 1 392 MHz, 22 W | 1 330 MHz, 21 W | 1 274 MHz, 24 W |
| Secondes à plein régime | 4 | 4 | 3 |
 
- Chaque appel démarre au maximum (boost), puis macOS divise la puissance par deux après 3-4 s.
- L'effet s'aggrave au fil des appels : la chaleur s'accumule.
- La baisse de fréquence (~15-20 %) n'explique pas seule la baisse de débit (~30 %) :
  hypothèse, la limite de puissance touche aussi la mémoire et le reste de la puce.
**Vérification : 10 s de pause entre chaque appel**
 
| Protocole | Débit médian 7B | Min / max |
| --- | --- | --- |
| Sans pause | 56 tokens/s | 54 / 82 |
| Pause de 10 s | 81 tokens/s | 53 / 85 |
 
- Appels 1 à 9 : 80-84 tokens/s (proche des 86 d'Ollama à froid).
- Appels 10 à 15 : 53-68 tokens/s : la chaleur s'accumule malgré les pauses.
**Conclusions pour le protocole**
- Performance en rafale ≠ performance soutenue. Toujours dire laquelle on rapporte.
- Mesures de vitesse : garder une pause, mélanger l'ordre des modèles et des prompts,
  noter alimentation, mode d'énergie et machine (Mac16,6).
- Mesures de qualité (réussite des tâches) : pas concernées, inutile de ralentir.
- Lien avec le stage : les PC industriels sont souvent sans ventilateur. Un benchmark
  sur un appel isolé surestimerait la vitesse réelle en production.
**Autres observations faites pendant l'enquête**
- KV cache : `ollama ps` affiche 5,7 Go pour un fichier de 4,7 Go. Le Go en plus est surtout
  le KV cache réservé pour un contexte de 32 768 tokens.
- Méthode : on isole un problème en retirant les éléments un par un (script vs Ollama seul,
  GPU vs CPU, secteur vs batterie, avec ou sans pause).
## Temps jusqu'au premier token (TTFT), 7B
 
| Prompt | Taille | TTFT (3 mesures, sans cache) |
| --- | --- | --- |
| Court | ~55 tokens | 0,12-0,13 s |
| Long | 3 072 tokens | 4,15 / 3,98 / 3,98 s |
 
- Prédiction : 3 000 / 206 ≈ 14,6 s. Mesuré : 4,0 s.
- Prefill sur prompt long ≈ 770 tokens/s, contre 206 mesurés sur 40 tokens : le débit du prefill
  augmente avec la longueur du prompt (un prompt court ne donne pas assez de travail parallèle
  au GPU). Une mesure faite dans un régime ne s'extrapole pas à un autre.
- Coût marginal ≈ 1,3 ms par token de prompt. Conséquence pour le RAG : 3 000 tokens de
  documentation = environ 4 s d'attente de plus avant le premier caractère.
**Piège du cache de préfixe**
- 1ère version du script : TTFT long = 0,04 s sauf la toute première mesure (3,33 s).
  Ollama gardait le KV cache des prompts longs, malgré l'alternance court/long.
- Le cache survit même d'une exécution du script à l'autre tant que le modèle reste chargé.
- Correction : un identifiant unique (uuid) au DÉBUT de chaque prompt.
- Leçon : un cache peut fausser silencieusement un benchmark. À l'inverse, c'est un gain
  énorme pour un agent qui renvoie toujours le même long prompt système (×80 ici).
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
   Le prefill doit traiter tout le prompt avant de générer le premier token : environ 1,3 ms
   par token de prompt pour le 7B (0,13 s pour 55 tokens, 4,0 s pour 3 072).
4. Pourquoi « tokens / latence totale » sous-estime-t-il le vrai débit ?
   La latence totale inclut le prefill, le HTTP et la préparation, en plus de la génération.
   Pour le 7B en série, la cause principale était en fait le bridage de puissance.
5. 5. À température 0, les réponses sont-elles strictement identiques ?
   Non. Voir la section « Test de température » : 2 réponses différentes sur 5 à température 0.
## Médiane plutôt que moyenne
La médiane n'est presque pas affectée par une mesure aberrante (par exemple une mesure ralentie
par une tâche de fond), alors qu'une seule valeur extrême peut fausser la moyenne.

## Test de température (scripts/temperature_test.py)

**Protocole** : qwen2.5-coder:1.5b, même prompt (compteur de pièces) envoyé 5 fois
à chaque température, on compte les réponses différentes avec `len(set(answers))`.

**Prédictions (écrites AVANT la mesure)**
- Température 0 : 1 réponse différente sur 5 (toutes identiques), peut-être 2 de temps en temps.
- Température 0,8 : 5 sur 5. Raisonnement : une réponse fait ~500 tokens, chacun tiré au sort.
  Même avec 99 % de chances que chaque token soit identique, 0,99^500 ≈ 0,7 % de chances
  d'obtenir deux réponses entièrement identiques. Et dès qu'un token diffère, toute la suite
  diverge, puisque chaque token dépend des précédents.

**Résultats**

| Température | Réponses différentes sur 5 |
| --- | --- |
| 0 | 2 |
| 0,8 | 5 |

**Analyse**
- 0,8 : prédiction vérifiée. Sur des réponses longues, une température même modérée
  produit des réponses toutes différentes. Utile pour le best-of-N (étape 6) : générer
  plusieurs réponses variées et garder celle qui passe le vérificateur.
- 0 : la température 0 n'est pas déterministe (déjà vu : 656 puis 655 tokens).
  Causes probables :
  - calculs en virgule flottante sur GPU : l'ordre des opérations peut changer
    légèrement le résultat ;
  - hypothèse : le 1er appel calcule le prefill de zéro, les suivants réutilisent le cache
    de préfixe. Deux chemins de calcul légèrement différents : quand deux tokens ont des
    probabilités presque égales, une infime différence fait basculer le choix.

**Conséquence pour le protocole**
- Même à température 0, répéter chaque tâche plusieurs fois et rapporter la variabilité
  (intervalles de confiance, étape 5). Ne jamais supposer qu'un seul essai suffit.
 