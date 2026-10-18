package tn.zitouna.ai.orchestration;

import java.util.Locale;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import lombok.RequiredArgsConstructor;
import tn.zitouna.ai.AiServiceException;
import tn.zitouna.ai.cropyield.YieldClient;
import tn.zitouna.ai.cropyield.YieldResult;
import tn.zitouna.ai.price.PriceClient;
import tn.zitouna.ai.price.PriceResult;
import tn.zitouna.ai.trees.TreeCountClient;
import tn.zitouna.ai.trees.TreeCountResult;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;
import tn.zitouna.parcel.Parcel;
import tn.zitouna.parcel.ParcelService;

/**
 * The flagship chain of the demo: the farmer uploads a parcel image, M6 counts the trees,
 * M3 turns that into an expected harvest, M4 says whether to sell now or store.
 */
@Service
@RequiredArgsConstructor
public class HarvestPlanService {

    /** Kg of oil per kg of olives. Tunisian mills range 13% to 31% (ONAGRI); 20% is a typical average. */
    static final double OIL_EXTRACTION_RATE = 0.20;

    private final TreeCountClient treeCountClient;
    private final YieldClient yieldClient;
    private final PriceClient priceClient;
    private final ParcelService parcelService;
    private final HistoryService historyService;

    public HarvestPlan plan(Long userId, Long parcelId, MultipartFile parcelImage) {
        Parcel parcel = parcelService.getOwned(userId, parcelId);
        boolean mock = false;

        // 1. M6: how many trees?
        int treeCount;
        String source;
        if (parcelImage != null && !parcelImage.isEmpty()) {
            TreeCountResult counted = treeCountClient.count(parcelImage);
            treeCount = counted.treeCount();
            source = "M6";
            mock |= counted.mock();
            if (!counted.mock()) {
                parcelService.updateTreeCount(userId, parcelId, treeCount);
            }
        } else if (parcel.getTreeCount() != null) {
            treeCount = parcel.getTreeCount();
            source = "PARCEL";
        } else {
            throw new AiServiceException(HttpStatus.BAD_REQUEST,
                    "Unknown tree count: upload a parcel image or set the tree count on the parcel");
        }

        // 2. M3: expected harvest for this many trees in this region.
        YieldResult yield = yieldClient.predict(
                new YieldClient.Request(parcel.getGovernorate(), YieldClient.currentSeason(), treeCount,
                        parcel.getAreaHa()));
        mock |= yield.mock();
        Double oilKg = yield.parcelEstimateKg() == null ? null : yield.parcelEstimateKg() * OIL_EXTRACTION_RATE;

        // 3. M4: sell now or store?
        PriceResult price = priceClient.predict(new PriceClient.Request(8, oilKg));
        mock |= price.mock();

        String summary = String.format(Locale.FRANCE,
                "%d arbres, récolte estimée %.0f kg d'olives (≈ %.0f kg d'huile). Conseil : %s.",
                treeCount,
                yield.parcelEstimateKg() == null ? 0 : yield.parcelEstimateKg(),
                oilKg == null ? 0 : oilKg,
                PriceResult.SELL_NOW.equals(price.recommendation()) ? "vendre maintenant" : "stocker");

        HarvestPlan plan = new HarvestPlan(treeCount, source, yield, oilKg, price, summary, mock);
        historyService.record(userId, parcelId, PredictionType.HARVEST_PLAN,
                Map.of("treeCountSource", source), plan);
        return plan;
    }
}
