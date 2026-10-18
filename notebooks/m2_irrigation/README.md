# M2 · Irrigation & alertes météo — notebooks

| | |
|---|---|
| Données | Open-Meteo **ERA5** journalier (ET₀ FAO, pluie, Tmax, Tmin), 12 gouvernorats oléicoles (Sfax, Sousse, Monastir, Mahdia, Kairouan, Sidi Bouzid, Gabès, Médenine, Nabeul, Zaghouan, Béja, Kasserine), 2014 → J−7 |
| Découpage | chronologique : train 2014–2021 · validation 2022 · test 2023 → aujourd'hui (jamais mélangé) |
| Baselines | « même jour l'an dernier » (baseline du plan) · persistance (moyenne des 7 derniers jours) |
| Modèles | **LSTM** global (30 jours → ET₀ des 16 jours suivants) · **Prophet** (un modèle par région, réentraîné à chaque date de prévision) |
| Métriques | MAE et RMSE de l'ET₀ prévue (mm/j), horizons 1 à 7 jours |
| Export | `models/m2/lstm_et0.npz` (poids + normalisation) · `metadata.json` |

## Fichiers

| Fichier | Rôle |
|---|---|
| `m2_common.py` | Téléchargement Open-Meteo (avec reprises et cache dans `data/raw/m2_irrigation/`), nettoyage, fenêtres, baselines, Prophet, LSTM, métriques, export. Le calcul NumPy du LSTM est le même que dans le service. |
| `train_m2.ipynb` | Tout le pipeline : données → EDA → découpage → baselines → LSTM → Prophet → résultats → export. ~15 min sur CPU (dont ~10 min de Prophet). |

## Résultats (test 2023-01 → 2026-09, 16 356 prévisions)

| Modèle | MAE (mm/j) | RMSE (mm/j) |
|---|---|---|
| Même jour l'an dernier (baseline) | 1,057 | 1,448 |
| Persistance 7 jours | 0,796 | 1,069 |
| **LSTM (servi)** | **0,706** | **0,980** |

Sur les dates où Prophet a aussi été évalué (une date tous les 28 jours × 12 régions = 588 prévisions) :
baseline 0,974 · persistance 0,738 · Prophet 0,666 · **LSTM 0,657** mm/j.

- Le LSTM réduit l'erreur de **33 %** par rapport à la baseline du plan, et de 11 % par rapport à la persistance.
- Prophet est presque aussi bon, mais il doit être réentraîné à chaque prévision (lent) et ne gère qu'une série
  par modèle. Le LSTM tourne en quelques millisecondes en NumPy dans le service.
- Pour une parcelle type (2,5 ha, 250 arbres), l'erreur moyenne du LSTM correspond à environ **46 L par arbre et par
  jour**, contre 69 L pour la baseline.
- Contrôle en conditions réelles (17/10/2026, Sfax) : ET₀ du LSTM de 3,3 à 3,7 mm/j, contre 3,0 à 3,4 mm/j pour la
  prévision numérique d'Open-Meteo.

**Limites (à dire dans le rapport)** : ERA5 est une réanalyse sur une grille d'environ 25 km, pas une station
sur la parcelle. Le modèle prévoit l'ET₀, mais la pluie et les températures des alertes viennent de la prévision
Open-Meteo. Le Kc de 0,65 est la valeur FAO-56 d'une oliveraie adulte : il varie selon l'âge et la densité.

## Exécuter

Avec Python 3.12 :

```bash
pip install -r notebooks/requirements-train.txt
cd notebooks/m2_irrigation
jupyter nbconvert --to notebook --execute train_m2.ipynb --output outputs/train_m2_executed.ipynb
```

Sans Python, avec Docker (depuis la racine du repo) :

```bash
docker build -t zitounai-train -f notebooks/Dockerfile.train notebooks
docker run --rm -v "${PWD}:/repo" -w /repo/notebooks/m2_irrigation zitounai-train jupyter nbconvert --to notebook --execute train_m2.ipynb --output outputs/train_m2_executed.ipynb
```

Ensuite, redémarrez le service pour charger le nouveau modèle : `docker compose restart m2-irrigation`. Pour le
partager : `python scripts/models.py push m2`.

## Conventions équipe

- Le notebook s'exécute de haut en bas sur un noyau frais, et ses **sorties sont dépouillées avant commit** : la version exécutée, avec les figures, est dans `outputs/` (non commité).
- `data/` et `models/` ne sont jamais commités.
