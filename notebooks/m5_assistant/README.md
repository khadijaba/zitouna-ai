# M5 · Assistant en derja — notebooks

| | |
|---|---|
| Données | `data/m5_intents.csv` : **500 questions écrites par l'équipe** (9 intentions, environ 55 chacune), en arabizi, en écriture arabe et en français · test indépendant : `ai-services/m5-assistant/tests/data/m5_probe_set.csv` (25 questions, aucun recouvrement) |
| Prétraitement | `normalize()` du service, importé tel quel : identique à l'inférence |
| Baseline | TF-IDF mots (1–2) + régression logistique (le plan) |
| Modèles | **TF-IDF caractères (2–5) + LR** · union mots + caractères + LR |
| Métriques | F1 macro en validation croisée stratifiée (5 plis) et sur un test de 20 %, justesse sur le probe set |
| Export | `models/m5_ensemble/` : `tfidf.joblib` + `config.json` (`weight_setfit = 0`) |

## Résultats

| Modèle | F1 macro CV | F1 macro test 20 % | Probe set |
|---|---|---|---|
| TF-IDF mots + LR (baseline) | 0,719 | 0,628 | 16 / 25 |
| **TF-IDF caractères + LR (servi)** | **0,753** | 0,688 | **19 / 25** |
| TF-IDF mots + caractères + LR | 0,749 | 0,704 | 18 / 25 |

- Les n-grammes de **caractères** gèrent mieux les orthographes variables de l'arabizi (`9adech` / `kadech`,
  `zitoun` / `zitouni`) : +3,4 points de F1 et +3 questions du probe set par rapport à la baseline.
- **Seuil de clarification : 0,35.** Sous ce seuil, l'assistant pose une question au lieu de deviner. En validation
  croisée, il répond directement à environ 3 questions sur 4, avec au moins 85 % de bonnes réponses.
- Le notebook ajoute aussi les règles du service : la garde « domaine » ne répond jamais « hors sujet » à une
  question qui parle d'olives.

**Limites** : 500 questions, c'est peu ; les confusions principales sont irrigation / conseil général et récolte /
comptage (voir la matrice de confusion). Le plan prévoyait aussi un modèle de type BERT fine-tuné : le service
accepte toujours l'ensemble TF-IDF + SetFit (`weight_setfit > 0` et dossier `setfit/`), à entraîner sur Colab
(GPU, téléchargement d'environ 1 Go), puis à comparer avec ce modèle sur le même probe set.

## Exécuter

```bash
pip install -r notebooks/requirements-train.txt scikit-learn==1.6.1 joblib
cd notebooks/m5_assistant
jupyter nbconvert --to notebook --execute train_m5.ipynb --output outputs/train_m5_executed.ipynb
```

Ensuite : `docker compose restart m5-assistant`. Pour ajouter des questions, complétez `data/m5_intents.csv`
(colonnes `text,intent`) et relancez le notebook. N'y mettez jamais les phrases du probe set.
