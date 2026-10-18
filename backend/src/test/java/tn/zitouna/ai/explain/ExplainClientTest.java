package tn.zitouna.ai.explain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import com.sun.net.httpserver.HttpServer;

import tn.zitouna.ai.AiServiceException;
import tn.zitouna.config.AiProperties;

/** ExplainClient against a real local HTTP server standing in for M5. */
class ExplainClientTest {

    private HttpServer server;
    private final AtomicReference<String> sentBody = new AtomicReference<>();

    @AfterEach
    void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    private ExplainClient clientFor(int status, String body) throws IOException {
        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/explain", exchange -> {
            sentBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.start();
        String url = "http://localhost:" + server.getAddress().getPort();
        AiProperties props = new AiProperties(Duration.ofSeconds(30), null, null, null, null, url, null);
        return new ExplainClient(RestClient.builder(), props, Duration.ofSeconds(2));
    }

    @Test
    void returnsTheLlmExplanation() throws IOException {
        ExplainResult result = clientFor(200, """
                {"explanation":"Arrosez 511 litres par arbre.","provider":"gemini","model":"gemini-3.5-flash",
                 "latencyMs":900,"fallback":false}""")
                .explain(new ExplainRequest("M2", Map.of("litersPerTree", 511), null));
        assertThat(result.explanation()).isEqualTo("Arrosez 511 litres par arbre.");
        assertThat(result.fallback()).isFalse();
        assertThat(result.mock()).isFalse();
        assertThat(sentBody.get()).contains("\"module\":\"M2\"").contains("\"language\":\"fr\"");
    }

    @Test
    void neverSendsImagesOrCoordinatesToTheLlm() throws IOException {
        clientFor(200, """
                {"explanation":"86 arbres.","provider":"template","model":"template","latencyMs":0,"fallback":true}""")
                .explain(new ExplainRequest("M6",
                        Map.of("treeCount", 86, "annotatedImageBase64", "AAAA", "boxes", "[]"), "fr"));
        assertThat(sentBody.get()).contains("treeCount").doesNotContain("annotatedImageBase64").doesNotContain("boxes");
    }

    @Test
    void m5DownIsAServiceError() throws IOException {
        ExplainClient client = clientFor(500, "{}");
        assertThatThrownBy(() -> client.explain(new ExplainRequest("M1", Map.of(), "fr")))
                .isInstanceOf(AiServiceException.class);
    }
}
