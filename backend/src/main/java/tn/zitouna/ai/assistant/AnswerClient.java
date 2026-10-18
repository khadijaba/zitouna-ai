package tn.zitouna.ai.assistant;

import java.time.Duration;
import java.util.List;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import lombok.extern.slf4j.Slf4j;
import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.ai.AiServiceException;
import tn.zitouna.ai.assistant.modules.Fact;
import tn.zitouna.config.AiProperties;

/**
 * M5 · POST /answer: an LLM (Gemini, Groq... with rotation, see M5's llm.py) writes the reply in
 * derja from the facts. Never throws: empty means "use the template reply".
 */
@Slf4j
@Component
public class AnswerClient extends AiServiceClient {

    private final boolean enabled;

    public AnswerClient(RestClient.Builder builder, AiProperties props,
            @Value("${app.ai.llm-timeout:PT15S}") Duration timeout,
            @Value("${app.ai.llm-enabled:true}") boolean enabled) {
        super("M5 LLM answer", props.assistantUrl(), builder, timeout);
        this.enabled = enabled;
    }

    public Optional<Answer> answer(Request request) {
        if (!enabled) {
            return Optional.empty();
        }
        try {
            return Optional.of(postJson("/answer", request, Answer.class));
        } catch (AiServiceException e) {
            log.info("No LLM answer, using the template reply: {}", e.getMessage());
            return Optional.empty();
        }
    }

    public record Request(String question, Intent intent, List<Fact> facts, Parcel parcel, String draft) {
    }

    /** Parcel profile sent to the LLM. No personal data (no owner, no email). */
    public record Parcel(String name, String governorate, Integer treeCount, Double areaHa, String variety,
            Boolean irrigated) {
    }

    public record Answer(String answer, String provider, String model, long latencyMs) {

        public String generatedBy() {
            return provider + "/" + model;
        }
    }
}
