package tn.zitouna.status;

import java.lang.management.ManagementFactory;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.sql.DataSource;

import org.springframework.boot.SpringBootVersion;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import tn.zitouna.config.AiProperties;

/** Checks the database and pings the six AI services (GET /health) in parallel, 2 s max each. */
@Service
public class StatusService {

    private static final Duration PING_TIMEOUT = Duration.ofSeconds(2);

    private record Target(String id, String name, String type, String baseUrl) {
    }

    private final DataSource dataSource;
    private final List<Target> targets;
    private final RestClient http;

    public StatusService(DataSource dataSource, AiProperties ai, RestClient.Builder builder) {
        this.dataSource = dataSource;
        this.targets = List.of(
                new Target("M1", "Maladies des feuilles", "Vision · classification", ai.diseaseUrl()),
                new Target("M2", "Irrigation & alertes météo", "Séries temporelles (LSTM)", ai.irrigationUrl()),
                new Target("M3", "Prévision du rendement", "Régression tabulaire", ai.yieldUrl()),
                new Target("M4", "Prix & moment de vente", "Séries temporelles (SARIMA)", ai.priceUrl()),
                new Target("M5", "Assistant en derja", "NLP · intentions + LLM", ai.assistantUrl()),
                new Target("M6", "Comptage des oliviers", "Vision · détection", ai.treesUrl()));
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(PING_TIMEOUT);
        requestFactory.setReadTimeout(PING_TIMEOUT);
        this.http = builder.clone().requestFactory(requestFactory).build();
    }

    public StatusResponse status() {
        try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
            var pings = targets.stream().map(t -> CompletableFuture.supplyAsync(() -> ping(t), pool)).toList();
            var database = CompletableFuture.supplyAsync(this::database, pool);
            return new StatusResponse(application(), database.join(),
                    pings.stream().map(CompletableFuture::join).toList(), Instant.now());
        }
    }

    private StatusResponse.Application application() {
        var runtime = ManagementFactory.getRuntimeMXBean();
        Instant started = Instant.ofEpochMilli(runtime.getStartTime());
        String version = getClass().getPackage().getImplementationVersion();
        return new StatusResponse.Application("Zitouna AI backend", version != null ? version : "dev",
                SpringBootVersion.getVersion(), Runtime.version().toString(), started,
                Duration.ofMillis(runtime.getUptime()).toSeconds());
    }

    private StatusResponse.Database database() {
        try (Connection connection = dataSource.getConnection()) {
            DatabaseMetaData meta = connection.getMetaData();
            return new StatusResponse.Database(connection.isValid(2), meta.getDatabaseProductName(),
                    meta.getDatabaseProductVersion());
        } catch (Exception e) {
            return new StatusResponse.Database(false, null, null);
        }
    }

    private StatusResponse.Module ping(Target t) {
        long start = System.nanoTime();
        try {
            Map<?, ?> health = http.get().uri(t.baseUrl() + "/health").retrieve().body(Map.class);
            long latency = Duration.ofNanos(System.nanoTime() - start).toMillis();
            Object loaded = health == null ? null : health.get("modelLoaded");
            return new StatusResponse.Module(t.id(), t.name(), t.type(), true,
                    loaded instanceof Boolean b ? b : null, latency, null);
        } catch (Exception e) {
            return new StatusResponse.Module(t.id(), t.name(), t.type(), false, null, null,
                    "service injoignable");
        }
    }
}
