package tn.zitouna.ai.cropyield;

import tn.zitouna.ai.AiResult;

/**
 * Response of M3 POST /predict. Parcel fields are null without tree count and area.
 * {@code scope}: NATIONAL with the trained model (regionalProductionTonnes is then the production of Tunisia),
 * REGIONAL in mock mode. {@code observed}: the season is already published by FAOSTAT (not a forecast).
 */
public record YieldResult(
        String governorate,
        int season,
        double regionalProductionTonnes,
        Double kgPerTree,
        Double parcelEstimateKg,
        Double parcelLowKg,
        Double parcelHighKg,
        String modelVersion,
        boolean mock,
        String scope,
        Boolean observed) implements AiResult {

    public boolean national() {
        return "NATIONAL".equals(scope);
    }
}
