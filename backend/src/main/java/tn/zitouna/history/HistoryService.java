package tn.zitouna.history;

import java.time.Instant;
import java.util.Optional;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;
import tn.zitouna.ai.AiResult;
import tn.zitouna.common.PageResponse;
import tn.zitouna.parcel.ParcelRepository;
import tn.zitouna.user.UserRepository;
import tools.jackson.databind.json.JsonMapper;

@Service
@RequiredArgsConstructor
public class HistoryService {

    private final PredictionRepository predictions;
    private final UserRepository users;
    private final ParcelRepository parcels;
    private final JsonMapper json;

    /**
     * Saves one AI call. {@code parcelId} may be null (e.g. a leaf photo not linked to a parcel).
     * {@code request} should be a small summary, never the raw image bytes.
     */
    @Transactional
    public void record(Long userId, Long parcelId, PredictionType type, Object request, AiResult response) {
        PredictionRecord record = new PredictionRecord();
        record.setUser(users.getReferenceById(userId));
        record.setParcel(parcelId == null ? null : parcels.getReferenceById(parcelId));
        record.setType(type);
        record.setRequestJson(request == null ? null : json.writeValueAsString(request));
        record.setResponseJson(json.writeValueAsString(response));
        record.setMock(response.mock());
        predictions.save(record);
    }

    /** Latest result of a module for this user (and parcel, if given), e.g. the last leaf diagnosis. */
    @Transactional(readOnly = true)
    public <T> Optional<Latest<T>> latest(Long userId, Long parcelId, PredictionType type, Class<T> resultType) {
        Optional<PredictionRecord> record = parcelId == null
                ? predictions.findFirstByUserIdAndTypeOrderByCreatedAtDesc(userId, type)
                : predictions.findFirstByUserIdAndParcelIdAndTypeOrderByCreatedAtDesc(userId, parcelId, type);
        return record.map(r -> new Latest<>(json.readValue(r.getResponseJson(), resultType), r.getCreatedAt()));
    }

    public record Latest<T>(T result, Instant createdAt) {
    }

    @Transactional(readOnly = true)
    public PageResponse<PredictionDto> list(Long userId, PredictionType type, Pageable pageable) {
        Page<PredictionRecord> page = type == null
                ? predictions.findByUserIdOrderByCreatedAtDesc(userId, pageable)
                : predictions.findByUserIdAndTypeOrderByCreatedAtDesc(userId, type, pageable);
        return PageResponse.of(page, PredictionDto::from);
    }
}
