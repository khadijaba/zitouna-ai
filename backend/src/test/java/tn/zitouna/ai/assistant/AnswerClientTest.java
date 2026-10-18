package tn.zitouna.ai.assistant;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import com.sun.net.httpserver.HttpServer;

import tn.zitouna.config.AiProperties;

/** AnswerClient against a real local HTTP server: never throws, empty = use the template. */
class AnswerClientTest {

    private static final AnswerClient.Request REQUEST =
            new AnswerClient.Request("9adech nesgi?", Intent.IRRIGATION, List.of(), null, "draft");

    private HttpServer server;
    private final AtomicInteger calls = new AtomicInteger();

    @AfterEach
    void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    private AnswerClient clientFor(int status, String body, boolean enabled) throws IOException {
        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/answer", exchange -> {
            calls.incrementAndGet();
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.start();
        String url = "http://localhost:" + server.getAddress().getPort();
        AiProperties props = new AiProperties(Duration.ofSeconds(30), null, null, null, null, url, null);
        return new AnswerClient(RestClient.builder(), props, Duration.ofSeconds(2), enabled);
    }

    @Test
    void parsesTheLlmAnswer() throws IOException {
        var answer = clientFor(200, """
                {"answer":"Esgi 6 marrat.","provider":"gemini","model":"gemini-3.5-flash","latencyMs":950}""", true)
                .answer(REQUEST);
        assertThat(answer).hasValueSatisfying(a -> {
            assertThat(a.answer()).isEqualTo("Esgi 6 marrat.");
            assertThat(a.generatedBy()).isEqualTo("gemini/gemini-3.5-flash");
        });
    }

    @Test
    void allLlmsDownMeansEmpty() throws IOException {
        assertThat(clientFor(503, "{\"detail\":\"All LLMs failed\"}", true).answer(REQUEST)).isEmpty();
    }

    @Test
    void disabledDoesNotCallM5() throws IOException {
        assertThat(clientFor(200, "{}", false).answer(REQUEST)).isEmpty();
        assertThat(calls.get()).isZero();
    }
}
