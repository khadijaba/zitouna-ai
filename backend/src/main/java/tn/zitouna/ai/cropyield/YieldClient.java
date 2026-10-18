package tn.zitouna.ai.cropyield;

import java.time.LocalDate;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.config.AiProperties;

/** M3 · Yield forecast (tabular regression). */
@Component
public class YieldClient extends AiServiceClient {

    public YieldClient(RestClient.Builder builder, AiProperties props) {
        super("M3 yield service", props.yieldUrl(), builder, props.timeout());
    }

    public YieldResult predict(Request request) {
        return postJson("/predict", request, YieldResult.class);
    }

    /** The olive season is named after the year the harvest starts (Oct-Feb): 2026 = 2026/2027. */
    public static int currentSeason() {
        LocalDate today = LocalDate.now();
        return today.getMonthValue() >= 9 ? today.getYear() : today.getYear() - 1;
    }

    /** areaHa (optional) gives a better parcel estimate than the tree count alone. */
    public record Request(String governorate, int season, Integer treeCount, Double areaHa) {
    }
}
