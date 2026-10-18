package tn.zitouna.status;

import java.time.Instant;
import java.util.List;

/** Live state of the platform, shown on the backend home page (GET /). */
public record StatusResponse(
        Application application,
        Database database,
        List<Module> modules,
        Instant checkedAt) {

    public record Application(String name, String version, String springBootVersion, String javaVersion,
            Instant startedAt, long uptimeSeconds) {
    }

    /** product/version are null when the database cannot be reached. */
    public record Database(boolean up, String product, String version) {
    }

    /**
     * One FastAPI service. {@code modelLoaded}: true with a trained model, false in demo (mock) mode,
     * null when the service is down. {@code error} explains why it is down.
     */
    public record Module(String id, String name, String type, boolean up, Boolean modelLoaded, Long latencyMs,
            String error) {
    }
}
