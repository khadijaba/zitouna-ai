package tn.zitouna.ai.explain;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.config.AiProperties;

/**
 * M5 · POST /explain: an LLM (Gemini, Groq in fallback) explains the result of any module in plain words.
 * M5 always answers 200 (template sentence when no LLM is available); a failure means M5 itself is down.
 */
@Component
public class ExplainClient extends AiServiceClient {

    private static final List<String> HEAVY_KEYS = List.of("base64", "image", "heatmap", "boxes");

    public ExplainClient(RestClient.Builder builder, AiProperties props,
            @Value("${app.ai.llm-timeout:PT15S}") Duration timeout) {
        super("M5 LLM explain", props.assistantUrl(), builder, timeout);
    }

    public ExplainResult explain(ExplainRequest request) {
        var body = new M5Request(request.module(), withoutHeavyData(request.result()), request.languageOrDefault());
        return postJson("/explain", body, ExplainResult.class);
    }

    /** Drops images and coordinates (useless to the LLM, and they can weigh megabytes). */
    static Map<String, Object> withoutHeavyData(Map<String, Object> result) {
        Map<String, Object> light = new LinkedHashMap<>();
        result.forEach((key, value) -> {
            String lower = key.toLowerCase(Locale.ROOT);
            if (HEAVY_KEYS.stream().noneMatch(lower::contains)) {
                light.put(key, value);
            }
        });
        return light;
    }

    record M5Request(String module, Map<String, Object> result, String language) {
    }
}
