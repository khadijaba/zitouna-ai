package tn.zitouna.ai;

import org.springframework.http.HttpStatus;

import lombok.Getter;

@Getter
public class AiServiceException extends RuntimeException {

    private final HttpStatus status;

    public AiServiceException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }
}
