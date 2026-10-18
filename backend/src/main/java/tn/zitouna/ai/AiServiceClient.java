package tn.zitouna.ai;

import java.time.Duration;
import java.util.function.Supplier;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.multipart.MultipartFile;

/**
 * Base class for the six module clients. Handles timeouts and turns any failure of a
 * FastAPI service into an {@link AiServiceException} (400 if the service rejected the
 * input, 503 if it is down), so one broken module never crashes the backend.
 */
public abstract class AiServiceClient {

    private final String module;
    private final RestClient http;

    protected AiServiceClient(String module, String baseUrl, RestClient.Builder builder, Duration timeout) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        Duration maxConnect = Duration.ofSeconds(5);
        requestFactory.setConnectTimeout(timeout.compareTo(maxConnect) < 0 ? timeout : maxConnect);
        requestFactory.setReadTimeout(timeout);
        this.module = module;
        this.http = builder.clone().baseUrl(baseUrl).requestFactory(requestFactory).build();
    }

    protected <T> T postJson(String path, Object body, Class<T> responseType) {
        return call(() -> http.post()
                .uri(path)
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(responseType));
    }

    /** Sends the image as multipart field "image", as every vision service expects. */
    protected <T> T postImage(String path, MultipartFile image, Class<T> responseType) {
        MultipartBodyBuilder parts = new MultipartBodyBuilder();
        String contentType = image.getContentType() != null ? image.getContentType() : MediaType.APPLICATION_OCTET_STREAM_VALUE;
        parts.part("image", image.getResource()).contentType(MediaType.parseMediaType(contentType));
        return call(() -> http.post()
                .uri(path)
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(parts.build())
                .retrieve()
                .body(responseType));
    }

    private <T> T call(Supplier<T> request) {
        try {
            T result = request.get();
            if (result == null) {
                throw new AiServiceException(HttpStatus.BAD_GATEWAY, module + " returned an empty response");
            }
            return result;
        } catch (HttpClientErrorException e) {
            throw new AiServiceException(HttpStatus.BAD_REQUEST,
                    module + " rejected the request: " + e.getResponseBodyAsString());
        } catch (RestClientException e) {
            throw new AiServiceException(HttpStatus.SERVICE_UNAVAILABLE, module + " is unavailable: " + e.getMessage());
        }
    }
}
