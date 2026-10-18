# M3 · Prévision du rendement — notebooks

**Plan B du plan de projet** : les productions par gouvernorat (rapports ONAGRI en PDF) ne sont pas disponibles en
données ouvertes, donc le modèle prévoit la **production nationale** de la Tunisie, puis le rendement par hectare
appliqué à la parcelle. Si l'équipe extrait les chiffres ONAGRI par gouvernorat, le même pipeline peut être
entraîné par région.

| | |
|---|---|
| Données | **FAOSTAT** (Tunisie, olives : production, surface récoltée, rendement, 1961 → 2024, export « bulk » Afrique) · **ERA5** journalier (Open-Meteo) 1960 → aujourd'hui, moyenné sur 12 gouvernorats oléicoles |
| Variables | production des 2 saisons précédentes (alternance des « bonnes » et « mauvaises » années), tendance, pluie septembre → mai, pluie d'été, jours ≥ 35 °C en avril-mai (floraison), Tmax moyenne de l'été |
| Validation | **chronologique glissante**, 2005 → 2024 : chaque saison est prévue par un modèle entraîné uniquement sur les saisons précédentes |
| Baselines | régression linéaire (le plan) · « comme la saison précédente » |
| Modèles | Ridge · **Random Forest** · Gradient Boosting |
| Export | `models/m3/model.joblib` · `history.csv` · `metadata.json` |

## Fichiers

| Fichier | Rôle |
|---|---|
| `m3_common.py` | Téléchargement FAOSTAT et ERA5 (cache dans `data/raw/m3_yield/`), variables saisonnières, modèles, prévisions glissantes, export. |
| `train_m3.ipynb` | Données → EDA → prévisions glissantes → comparaison → incertitude → export. ~2 min sur CPU (téléchargement ERA5 la 1ʳᵉ fois : plusieurs minutes). |

## Résultats (20 saisons de test, 2005 → 2024)

| Modèle | MAE (t) | MAPE |
|---|---|---|
| Comme la saison précédente | 540 000 | 60,7 % |
| Régression linéaire (baseline) | 465 000 | 55,7 % |
| Ridge | 453 000 | 52,3 % |
| Gradient Boosting | 448 000 | 46,0 % |
| **Random Forest (servi)** | **396 000** | **40,6 %** |

- Le Random Forest réduit l'erreur de **27 %** par rapport à la régression linéaire du plan.
- Une erreur de 40 % peut sembler forte, mais la production tunisienne varie énormément d'une année sur l'autre : de
  0,7 Mt en 2021 à 2,0 Mt en 2020. Prévoir une saison un an à l'avance avec la météo est difficile, et le rapport
  doit le dire.
- L'intervalle de la parcelle vient des **vraies erreurs du test** : de −53 % à +90 % (quantiles 10 % et 90 %).

**Limites (à dire dans le rapport)** : prévision nationale et non régionale (plan B) ; 64 saisons seulement ;
la surface récoltée FAOSTAT varie beaucoup selon les années ; sans la surface de la parcelle, l'estimation par
arbre utilise environ 100 millions d'oliviers en Tunisie (chiffre ONH / ministère de l'Agriculture).

## Utilisation par le service

- Saison déjà publiée par FAOSTAT (≤ 2024) : le chiffre réel est renvoyé (`observed: true`).
- Saisons suivantes : prévues l'une après l'autre (la prévision de 2025 sert de « saison précédente » pour 2026).
- Saison dont la météo n'est pas encore complète : moyenne météo des 10 dernières saisons.
- Relancer le notebook chaque année après août (nouvelle saison météo complète, nouvelles données FAOSTAT).

## Exécuter

```bash
pip install -r notebooks/requirements-train.txt scikit-learn==1.6.1
cd notebooks/m3_yield
jupyter nbconvert --to notebook --execute train_m3.ipynb --output outputs/train_m3_executed.ipynb
```

Avec Docker : voir [`../README.md`](../README.md) (image `Dockerfile.train`). Ensuite : `docker compose restart m3-yield`.
