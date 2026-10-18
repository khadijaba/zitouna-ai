# M4 · Prix et moment de vente — notebooks

| | |
|---|---|
| Données | Prix mensuel de l'huile d'olive extra vierge, **FMI** (série FRED `POLVOILUSDM`, USD/t, 1992 → dernier mois publié), converti en **TND/kg** avec le taux de change officiel annuel de la **Banque mondiale** (`PA.NUS.FCRF`) |
| Découpage | chronologique : train ≤ 2016 · validation 2017–2020 · test 2021 → aujourd'hui |
| Baseline | naïve (le prix reste celui du dernier mois) |
| Modèles | **SARIMA** sur le log du prix (ordre choisi par AIC) · **LSTM** (ensemble de 5 graines, sur les rendements log) |
| Évaluation | prévisions **glissantes** : à chaque mois du test, le modèle ne voit que le passé (SARIMA réajusté chaque mois) |
| Métriques | MAPE par horizon (1 à 6 mois) · **gain simulé** du conseil vendre / stocker face à « toujours vendre tout de suite » |
| Export | `models/m4/model.json` · `prices.csv` · `metadata.json` |

## Fichiers

| Fichier | Rôle |
|---|---|
| `m4_common.py` | Téléchargement FRED et Banque mondiale (cache dans `data/raw/m4_price/`), série TND/kg, SARIMA, LSTM, MAPE, simulation de la stratégie, export. |
| `train_m4.ipynb` | Tout le pipeline : données → EDA → baseline → SARIMA → LSTM → résultats → marge de décision → export. ~5 min sur CPU. |

## Résultats (test 2021-01 → 2026-06, 66 dates de prévision)

MAPE (%) par horizon :

| Modèle | 1 mois | 2 | 3 | 4 | 5 | 6 mois | moyenne |
|---|---|---|---|---|---|---|---|
| Naïf (baseline) | 4,22 | 7,53 | 10,53 | 13,38 | 16,02 | 18,70 | 11,73 |
| **SARIMA (0,1,1)(1,0,1)₁₂ (servi)** | **3,99** | **7,18** | **10,13** | **12,79** | **15,44** | **18,42** | **11,33** |
| LSTM | 4,18 | 7,75 | 10,57 | 13,34 | 16,16 | 18,62 | 11,77 |

L'intervalle à 80 % de SARIMA contient la vraie valeur dans 91 % (horizon 1) à 80 % (horizon 6) des cas : il est
bien calibré, un peu prudent à court terme.

**Conseil vendre / stocker** (61 décisions dont les 6 mois suivants sont connus) :

| Stratégie | % « stocker » | Gain moyen (TND/kg) | % stockages gagnants |
|---|---|---|---|
| Toujours vendre (référence) | 0 % | 0 | — |
| SARIMA sans marge | 43 % | **−0,47** | 65 % |
| **SARIMA, marge 4 % (servi)** | 16 % | **+0,10** | **90 %** |
| Oracle (connaît l'avenir) | — | +1,97 | — |

Sans marge, SARIMA a raison deux fois sur trois, mais ses erreurs pendant la chute des prix de 2024–2025 coûtent plus
que ce que rapportent ses bons conseils. La **marge de prudence** (stocker seulement si le gain net prévu dépasse 4 %
du prix du jour) a été choisie sur la **validation 2017–2020**, sans regarder le test. Sur le test, elle rend le
conseil rentable : 9 « stocker » sur 10 sont gagnants.

**Limites (à dire dans le rapport)** :
- Le test (2021–2026) contient le choc de la sécheresse espagnole (prix ×2,5, puis chute) : aucun modèle de série
  temporelle ne prévoit ces chocs, d'où l'écart avec l'oracle.
- Le LSTM n'apporte rien sur ~400 points mensuels : trop peu de données pour un réseau, résultat attendu et documenté.
- **Le prix est un prix mondial de référence** (huile extra vierge, Royaume-Uni), converti en dinars : il est plus
  élevé que le prix payé au producteur tunisien. Pour servir les **prix au producteur tunisiens du COI**, saisissez-les
  dans `data/raw/m4_price/coi_tunisia_producer.csv` (colonnes `date` au format `YYYY-MM` et `price_tnd_kg`, au moins
  60 mois) puis relancez le notebook : `build_series()` les utilise automatiquement et le champ `source` de l'API
  l'indique.

## Exécuter

Avec Python 3.12 :

```bash
pip install -r notebooks/requirements-train.txt
cd notebooks/m4_price
jupyter nbconvert --to notebook --execute train_m4.ipynb --output outputs/train_m4_executed.ipynb
```

Sans Python, avec Docker (depuis la racine du repo) :

```bash
docker build -t zitounai-train -f notebooks/Dockerfile.train notebooks
docker run --rm -v "${PWD}:/repo" -w /repo/notebooks/m4_price zitounai-train jupyter nbconvert --to notebook --execute train_m4.ipynb --output outputs/train_m4_executed.ipynb
```

Ensuite, redémarrez le service : `docker compose restart m4-price`. Chaque mois, relancer le notebook récupère le
dernier prix publié : supprimez d'abord `data/raw/m4_price/` (cache) ou appelez `build_series(force=True)`.

## Conventions équipe

- Le notebook s'exécute de haut en bas sur un noyau frais, et ses **sorties sont dépouillées avant commit** : la version exécutée, avec les figures, est dans `outputs/` (non commité).
- `data/` et `models/` ne sont jamais commités.
