package tn.zitouna.ai.assistant;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.Executors;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import com.sun.net.httpserver.HttpServer;

import tn.zitouna.config.AiProperties;

/** IntentClient against a real local HTTP server: parsing, timeout, errors. */
class IntentClientTest {

    private static final String OK_JSON = """
            {"intent":"meteo_alerte","confidence":0.91,"clarify":false,"question":null,
             "candidates":[{"intent":"meteo_alerte","score":0.91},{"intent":"irrigation","score":0.05},
                           {"intent":"conseil_general","score":0.02}],
             "modelsAgree":true,"entities":{"gouvernorat":"beja"},"modelVersion":"m5_ensemble","mock":false}""";

    private HttpServer server;
    private volatile long delayMs;

    @AfterEach
    void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    private IntentClient clientFor(int status, String body, long delay) throws IOException {
        delayMs = delay;
        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.setExecutor(Executors.newCachedThreadPool());
        server.createContext("/intent", exchange -> {
            try {
                Thread.sleep(delayMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.start();
        return client("http://localhost:" + server.getAddress().getPort());
    }

    private static IntentClient client(String url) {
        AiProperties props = new AiProperties(Duration.ofSeconds(30), null, null, null, null, url, null);
        return new IntentClient(RestClient.builder(), props, Duration.ofMillis(500));
    }

    @Test
    void parsesTheM5Response() throws IOException {
        IntentResponse res = clientFor(200, OK_JSON, 0).detect("fama jlid ghodwa fi beja?");
        assertThat(res.intent()).isEqualTo(Intent.METEO_ALERTE);
        assertThat(res.clarify()).isFalse();
        assertThat(res.modelsAgree()).isTrue();
        assertThat(res.entities().gouvernorat()).isEqualTo("beja");
        assertThat(res.candidates()).extracting(IntentResponse.Candidate::intent)
                .containsExactly(Intent.METEO_ALERTE, Intent.IRRIGATION, Intent.CONSEIL_GENERAL);
    }

    @Test
    void timeoutFallsBackToClarify() throws IOException {
        IntentClient client = clientFor(200, OK_JSON, 0);
        client.detect("warm-up"); // class loading must not count in the measured time
        delayMs = 2_000;

        long start = System.nanoTime();
        IntentResponse res = client.detect("slow");
        // 500 ms timeout: must give up well before the 2 s answer, and must not retry the POST.
        assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofMillis(900));
        assertThat(res.clarify()).isTrue();
        assertThat(res.question()).isEqualTo(IntentResponse.GENERIC_QUESTION);
    }

    @Test
    void serverErrorFallsBackToClarify() throws IOException {
        assertThat(clientFor(500, "{\"detail\":\"boom\"}", 0).detect("x").clarify()).isTrue();
    }

    @Test
    void unknownIntentFallsBackToClarify() throws IOException {
        assertThat(clientFor(200, OK_JSON.replace("\"intent\":\"meteo_alerte\"", "\"intent\":\"cuisine\""), 0)
                .detect("x").clarify()).isTrue();
    }

    @Test
    void serviceDownFallsBackToClarify() {
        assertThat(client("http://localhost:1").detect("x").clarify()).isTrue();
    }
}
