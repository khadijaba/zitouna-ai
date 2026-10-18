package tn.zitouna.config;

import java.time.Duration;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Base URLs of the six FastAPI services (see docs/api-contract.md). */
@ConfigurationProperties("app.ai")
public record AiProperties(
        Duration timeout,
        String diseaseUrl,
        String irrigationUrl,
        String yieldUrl,
        String priceUrl,
        String assistantUrl,
        String treesUrl) {
}
