package tn.zitouna.ai.price;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.config.AiProperties;

/** M4 · Price forecast and selling advice (time series). */
@Component
public class PriceClient extends AiServiceClient {

    public PriceClient(RestClient.Builder builder, AiProperties props) {
        super("M4 price service", props.priceUrl(), builder, props.timeout());
    }

    public PriceResult predict(Request request) {
        return postJson("/predict", request, PriceResult.class);
    }

    /** quantityKg: kg of oil the farmer could sell (used for expectedGainTnd), may be null. */
    public record Request(int horizonWeeks, Double quantityKg) {
    }
}
