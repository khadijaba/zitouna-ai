# Notebooks

One folder per module. Training runs on Google Colab or Kaggle (free GPU) when needed: mount the shared Drive and keep the same relative paths (`data/`, `models/`).

Experiment tracking (MLflow, owned by M3): log params, metrics and the baseline for every run, so the final comparison table (baseline vs final model, per module) can be built from MLflow. `mlruns/` is git-ignored.

## Modules entraînés

| Module | Notebook | Résultat sur le test | Détails |
|---|---|---|---|
| M1 · Maladies | `m1_disease/train_m1.ipynb` | MobileNetV3 : accuracy 97,1 %, F1 macro 0,969 (petit CNN 0,741) | [m1_disease/README.md](m1_disease/README.md) |
| M2 · Irrigation | `m2_irrigation/train_m2.ipynb` | LSTM : MAE de l'ET₀ 0,71 mm/j (−33 % vs « même jour l'an dernier ») | [m2_irrigation/README.md](m2_irrigation/README.md) |
| M3 · Rendement | `m3_yield/train_m3.ipynb` | Random Forest : MAPE 40,6 % (régression linéaire 55,7 %), production nationale | [m3_yield/README.md](m3_yield/README.md) |
| M4 · Prix | `m4_price/train_m4.ipynb` | SARIMA : MAPE 11,3 % (naïf 11,7 %) ; conseil vendre / stocker +0,10 TND/kg | [m4_price/README.md](m4_price/README.md) |
| M5 · Assistant | `m5_assistant/train_m5.ipynb` | TF-IDF caractères : F1 macro 0,75 (mots 0,72), probe set 19/25 | [m5_assistant/README.md](m5_assistant/README.md) |
| M6 · Comptage | détecteur OpenCV (pas d'entraînement) | erreur ≤ 5 % sur vergers synthétiques | [m6_tree_count/README.md](m6_tree_count/README.md) |

Environnement d'entraînement : `requirements-train.txt` (+ `scikit-learn==1.6.1` pour M3 / M5), ou l'image
`Dockerfile.train` (sans Python sur la machine).
