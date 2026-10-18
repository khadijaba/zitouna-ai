package tn.zitouna.ai.orchestration;

import tn.zitouna.ai.AiResult;
import tn.zitouna.ai.cropyield.YieldResult;
import tn.zitouna.ai.price.PriceResult;

/**
 * Result of the M6 -> M3 -> M4 chain.
 * treeCountSource: "M6" (counted from the uploaded image) or "PARCEL" (value saved on the parcel).
 */
public record HarvestPlan(
        int treeCount,
        String treeCountSource,
        YieldResult yield,
        Double estimatedOilKg,
        PriceResult price,
        String summary,
        boolean mock) implements AiResult {
}
