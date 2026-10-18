package tn.zitouna.ai.irrigation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.LocalDate;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.RestClient;

import com.sun.net.httpserver.HttpServer;

import tn.zitouna.ai.AiServiceException;
import tn.zitouna.ai.price.PriceClient;
import tn.zitouna.ai.price.PriceResult;
import tn.zitouna.config.AiProperties;

/** M2 and M4 clients against a real local HTTP server: request body, JSON mapping, failures. */
class IrrigationAndPriceClientTest {

    private HttpServer server;
    private final AtomicReference<String> lastBody = new AtomicReference<>();

    @AfterEach
    void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    private String serve(int status, String body) throws IOException {
        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/predict", exchange -> {
            lastBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.start();
        return "http://localhost:" + server.getAddress().getPort();
    }

    private static AiProperties props(String irrigationUrl, String priceUrl) {
        return new AiProperties(Duration.ofSeconds(5), null, irrigationUrl, null, priceUrl, null, null);
    }

    @Test
    void irrigationSendsCamelCaseAndParsesDaysAndAlerts() throws IOException {
        String url = serve(200, """
                {"days":[{"date":"2026-10-17","et0Mm":3.66,"rainMm":0.0,"waterNeedMm":2.38,"litersPerTree":237.9,"irrigate":true}],
                 "alerts":[{"date":"2026-10-18","type":"FROST","severity":"HIGH","message":"Risque de gel"}],
                 "modelVersion":"lstm-et0","mock":false}""");
        var client = new IrrigationClient(RestClient.builder(), props(url, null));

        IrrigationResult result = client.predict(new IrrigationClient.Request(34.74, 10.76, 250, 2.5, 14));

        assertThat(lastBody.get()).contains("\"treeCount\":250", "\"areaHa\":2.5", "\"days\":14");
        assertThat(result.mock()).isFalse();
        assertThat(result.days()).singleElement().satisfies(d -> {
            assertThat(d.date()).isEqualTo(LocalDate.of(2026, 10, 17));
            assertThat(d.litersPerTree()).isEqualTo(237.9);
            assertThat(d.irrigate()).isTrue();
        });
        assertThat(result.alerts()).singleElement().satisfies(a -> assertThat(a.type()).isEqualTo("FROST"));
    }

    @Test
    void priceParsesSourceAndIgnoresUnknownFields() throws IOException {
        String url = serve(200, """
                {"currency":"TND","unit":"kg",
                 "history":[{"date":"2026-07-15","price":18.54,"low":null,"high":null}],
                 "forecast":[{"date":"2026-10-24","price":18.6,"low":17.9,"high":19.3}],
                 "recommendation":"SELL_NOW","reason":"Aucune hausse nette attendue.","expectedGainTnd":null,
                 "modelVersion":"sarima","mock":false,"source":"FMI","futureField":42}""");
        var client = new PriceClient(RestClient.builder(), props(null, url));

        PriceResult result = client.predict(new PriceClient.Request(8, 1500.0));

        assertThat(lastBody.get()).contains("\"horizonWeeks\":8", "\"quantityKg\":1500.0");
        assertThat(result.source()).isEqualTo("FMI");
        assertThat(result.recommendation()).isEqualTo(PriceResult.SELL_NOW);
        assertThat(result.forecast()).singleElement().satisfies(p -> {
            assertThat(p.low()).isLessThanOrEqualTo(p.price());
            assertThat(p.high()).isGreaterThanOrEqualTo(p.price());
        });
        assertThat(result.history().getFirst().low()).isNull();
    }

    @Test
    void serviceDownGives503AndRejectedInputGives400() throws IOException {
        var down = new PriceClient(RestClient.builder(), props(null, "http://localhost:1"));
        assertThatThrownBy(() -> down.predict(new PriceClient.Request(8, null)))
                .isInstanceOfSatisfying(AiServiceException.class,
                        e -> assertThat(e.getStatus()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE));

        String url = serve(422, "{\"detail\":\"latitude must be <= 90\"}");
        var rejected = new IrrigationClient(RestClient.builder(), props(url, null));
        assertThatThrownBy(() -> rejected.predict(new IrrigationClient.Request(120, 10, null, null, 7)))
                .isInstanceOfSatisfying(AiServiceException.class,
                        e -> assertThat(e.getStatus()).isEqualTo(HttpStatus.BAD_REQUEST));
    }
}
