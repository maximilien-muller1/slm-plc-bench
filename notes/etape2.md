# Étape 2 — Les tâches

## 2.1 Prise en main du simulateur

### Le rôle des 4 fichiers (slm_plc_bench/st/)
Le simulateur lit le code comme on lit une phrase, en 4 étapes, dans cet ordre :

| Fichier | Rôle | Analogie avec une phrase |
| --- | --- | --- |
| `lexer.py` | Découpe le texte en tokens (mots-clés, noms, nombres, opérateurs) | Repérer les mots et la ponctuation |
| `parser.py` | Structure les tokens en arbre selon la grammaire du Structured Text | Analyse grammaticale (sujet, verbe, complément) |
| `semantic.py` | Vérifie le sens : variables déclarées, types compatibles | « Le chat aboie » : correct grammaticalement, mais absurde |
| `runtime.py` | Exécute le programme cycle automate par cycle (horloge simulée pour les TON) | Faire ce que dit la phrase |

Exemple sur `Motor := Start AND NOT Stop;` :
1. Lexer : `Motor`, `:=`, `Start`, `AND`, `NOT`, `Stop`, `;`
2. Parser : arbre « affecter à Motor le résultat de Start ET (NON Stop) »
3. Semantic : les 3 variables sont-elles déclarées ? Toutes des BOOL ? AND s'applique-t-il à des BOOL ?
4. Runtime : avec Start = TRUE et Stop = FALSE, calcule Motor = TRUE

Attention : le runtime ne mesure pas le temps de calcul, il fait tourner le programme.

### L'API à retenir
- `compile_st(code)` : lexer + parser + vérifications, renvoie le bloc vérifié (ou lève une `STError`)
- `Simulator(fb, cycle_ms=10)` : crée une instance du bloc
- `sim.set_inputs({...})` : pose les valeurs sur les entrées (comme appuyer sur un bouton)
- `sim.scan()` : exécute UN cycle automate, c'est là que les sorties sont calculées
- `sim.read("Nom")` : lit une variable

### Le cycle automate
Un vrai automate tourne en boucle toutes les quelques millisecondes : lire les entrées,
exécuter le programme, écrire les sorties. Dans le simulateur, c'est `scan()` qui déclenche un cycle.
Sans `scan()`, le bouton est bien appuyé (`set_inputs`) mais le programme ne s'exécute jamais :
comme appuyer sur le bouton d'une machine dont l'automate est éteint.

### Expérience : séquence marche / arrêt (scripts/try_simulator.py)
Prédiction, puis résultat :

| Moment | Entrée qui change | Prédiction | Résultat |
| --- | --- | --- | --- |
| 1 | Appui sur Marche | TRUE | TRUE |
| 2 | Relâche Marche | TRUE (auto-maintien) | TRUE |
| 3 | Appui sur Arrêt (contact fermé : Arret = FALSE) | FALSE (arrêt prioritaire) | FALSE |

- Auto-maintien : aucune condition du IF ne s'applique, donc Moteur garde sa valeur du cycle précédent.
- Piège du contact fermé : bouton d'arrêt NON appuyé = TRUE. Sinon le moteur ne démarre jamais.
- Avec un seul scan par moment (10 ms simulées), la temporisation de défaut (5 s) n'a pas le temps de se déclencher.

### Expérience : 3 erreurs volontaires

| Erreur provoquée | Message | Type |
| --- | --- | --- |
| Point-virgule oublié après `Moteur := FALSE` | `parse error: line 19: expected ';' at the end of the assignment, found 'ELSIF'` | Grammaire (parser) |
| Variable non déclarée (`Moteur := Demarrage;`) | `semantic error: line 20: undeclared variable DEMARRAGE` | Sens (semantic) |
| Boucle `WHILE` | `parse error: line 25: WHILE: loops are not allowed: a PLC scan must never block, use timers instead` | Grammaire (parser) |

**Erreur signalée une ligne trop tard (point-virgule)**
- Le point-virgule manque ligne 18, l'erreur est signalée ligne 19.
- Le parser lit les tokens un par un : il ne se rend compte qu'il manquait un `;` qu'en tombant
  sur le token suivant (`ELSIF`, ligne 19). Comportement de presque tous les compilateurs.
- Conséquence : un petit modèle risque de corriger au mauvais endroit (modifier la ligne 19).
- Idée à tester à l'étape 6 : un message plus explicite (« point-virgule manquant à la fin de
  la ligne 18 ») aide-t-il le petit modèle à mieux se corriger ?

**Un bon message d'erreur pour un modèle** donne la cause et la piste de correction,
comme celui de la boucle WHILE (« use timers instead »).

### Python appris
- Code Structured Text dans un fichier Python : le mettre dans une chaîne entre triples guillemets `"""..."""`.
- `texte.replace("ancien", "nouveau", 1)` : copie du texte avec seulement la 1re occurrence remplacée.
- `try / except STError as error` : attrape l'erreur pour afficher son message et continuer.
  Sans lui, le message s'affiche dans un traceback mais le script s'arrête net à la première erreur.
  Essentiel pour le benchmark : un code qui ne compile pas doit compter comme un échec,
  pas faire planter toute la série.
- `dictionnaire.items()` : parcourir les paires (clé, valeur) d'un dictionnaire.