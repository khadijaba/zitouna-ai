package tn.zitouna.ai.disease;

import java.util.Map;

import tn.zitouna.ai.AiResult;

/**
 * Response of M1 POST /predict. Labels: healthy, peacock_spot, aculus_olearius, olive_knot.
 * {@code lowConfidence}: calibrated confidence &lt; 0.70, no diagnosis is given and {@code advice} asks to retake
 * the photo (null for older services).
 */
public record DiseaseResult(
        String label,
        String labelFr,
        double confidence,
        Map<String, Double> probabilities,
        String advice,
        String heatmapBase64,
        String modelVersion,
        boolean mock,
        Boolean lowConfidence) implements AiResult {
}
