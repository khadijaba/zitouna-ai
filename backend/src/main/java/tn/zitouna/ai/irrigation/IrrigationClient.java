package tn.zitouna.ai.irrigation;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.config.AiProperties;

/** M2 · Irrigation and weather alerts (time series). */
@Component
public class IrrigationClient extends AiServiceClient {

    public IrrigationClient(RestClient.Builder builder, AiProperties props) {
        super("M2 irrigation service", props.irrigationUrl(), builder, props.timeout());
    }

    public IrrigationResult predict(Request request) {
        return postJson("/predict", request, IrrigationResult.class);
    }

    public record Request(double latitude, double longitude, Integer treeCount, Double areaHa, int days) {
    }
}
