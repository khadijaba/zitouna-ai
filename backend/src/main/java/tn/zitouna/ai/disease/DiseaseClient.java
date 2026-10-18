package tn.zitouna.ai.disease;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;

import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.config.AiProperties;

/** M1 · Leaf diseases (vision classification). */
@Component
public class DiseaseClient extends AiServiceClient {

    public DiseaseClient(RestClient.Builder builder, AiProperties props) {
        super("M1 disease service", props.diseaseUrl(), builder, props.timeout());
    }

    public DiseaseResult predict(MultipartFile leafImage) {
        return postImage("/predict", leafImage, DiseaseResult.class);
    }
}
