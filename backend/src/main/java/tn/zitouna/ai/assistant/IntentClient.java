package tn.zitouna.ai.assistant;

import java.time.Duration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import lombok.extern.slf4j.Slf4j;
import tn.zitouna.ai.AiServiceClient;
import tn.zitouna.ai.AiServiceException;
import tn.zitouna.config.AiProperties;

/**
 * M5 · intent detection. Short timeout (the farmer is waiting in the chat) and never throws:
 * any error or timeout becomes a "please clarify" answer.
 */
@Slf4j
@Component
public class IntentClient extends AiServiceClient {

    public IntentClient(RestClient.Builder builder, AiProperties props,
            @Value("${app.ai.assistant-timeout:PT3S}") Duration timeout) {
        super("M5 assistant service", props.assistantUrl(), builder, timeout);
    }

    public IntentResponse detect(String text) {
        try {
            IntentResponse response = postJson("/intent", new IntentRequest(text), IntentResponse.class);
            if (response.intent() == null) {
                throw new AiServiceException(HttpStatus.BAD_GATEWAY, "M5 returned no intent");
            }
            return response;
        } catch (AiServiceException e) {
            log.warn("Intent detection failed, asking the farmer to clarify: {}", e.getMessage());
            return IntentResponse.fallback();
        }
    }
}
