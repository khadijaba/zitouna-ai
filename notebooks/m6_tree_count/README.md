# M6 · Comptage des oliviers — notebooks

| | |
|---|---|
| Méthode servie | **Détection classique des couronnes avec OpenCV** (baseline du plan), sans entraînement : voir `ai-services/m6-tree-count/app/predictor.py` |
| Évaluation actuelle | vergers synthétiques à nombre d'arbres connu (tests automatiques du service) : erreur de comptage ≤ 5 % sur des arbres séparés, ≤ 10 % avec des couronnes qui se touchent |
| Étape suivante | YOLOv8 fine-tuné sur **OliveTreeCrownsDb** (Mendeley Data), comparé à OpenCV en mAP@0.5 et en erreur de comptage par image |
| Export attendu | `models/m6/best.pt` : le service l'utilise automatiquement s'il est présent (sinon OpenCV) |

## Comment marche le détecteur OpenCV

1. Score de végétation par pixel : vert en excès (2G − R − B sur les coordonnées chromatiques), plus l'assombrissement
   (les couronnes sont plus sombres que le sol nu entre les rangs).
2. Seuil d'Otsu → masque des couronnes, nettoyé par ouverture / fermeture morphologique.
3. Rayon typique d'une couronne = rayon médian des taches isolées.
4. Transformée de distance + maxima locaux espacés d'au moins un rayon : un arbre par maximum, ce qui sépare les
   couronnes qui se touchent.

**Limites** : les images doivent être vues du dessus (drone ou satellite), avec un sol plus clair que les arbres.
Une culture intercalaire verte, des ombres fortes ou des arbres très serrés font baisser la précision. YOLOv8,
entraîné sur des couronnes annotées, est la suite prévue par le plan.
