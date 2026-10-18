package tn.zitouna.history;

import java.time.Instant;

import com.fasterxml.jackson.annotation.JsonRawValue;

/** request/response are stored as JSON text and sent back as real JSON objects. */
public record PredictionDto(
        Long id,
        PredictionType type,
        Long parcelId,
        String parcelName,
        @JsonRawValue String request,
        @JsonRawValue String response,
        boolean mock,
        Instant createdAt) {

    public static PredictionDto from(PredictionRecord r) {
        return new PredictionDto(r.getId(), r.getType(),
                r.getParcel() == null ? null : r.getParcel().getId(),
                r.getParcel() == null ? null : r.getParcel().getName(),
                r.getRequestJson(), r.getResponseJson(), r.isMock(), r.getCreatedAt());
    }
}
