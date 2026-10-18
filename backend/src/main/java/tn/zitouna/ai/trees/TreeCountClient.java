package tn.zitouna.ai.trees;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;

import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.config.AiProperties;

/** M6 · Olive tree counting (object detection on drone/satellite images). */
@Component
public class TreeCountClient extends AiServiceClient {

    public TreeCountClient(RestClient.Builder builder, AiProperties props) {
        super("M6 tree counting service", props.treesUrl(), builder, props.timeout());
    }

    public TreeCountResult count(MultipartFile parcelImage) {
        return postImage("/predict", parcelImage, TreeCountResult.class);
    }
}
