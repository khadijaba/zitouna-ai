package tn.zitouna.history;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface PredictionRepository extends JpaRepository<PredictionRecord, Long> {

    // ---- Admin back-office (every user) ----

    @EntityGraph(attributePaths = { "parcel", "user" })
    Page<PredictionRecord> findAllByOrderByCreatedAtDesc(Pageable pageable);

    @EntityGraph(attributePaths = { "parcel", "user" })
    Page<PredictionRecord> findByTypeOrderByCreatedAtDesc(PredictionType type, Pageable pageable);

    long countByUserId(Long userId);

    long countByMockTrue();

    /** [type, count] for every module. */
    @Query("select p.type, count(p) from PredictionRecord p group by p.type")
    List<Object[]> countByType();

    @Query("select p.createdAt from PredictionRecord p where p.createdAt >= :since")
    List<Instant> createdSince(Instant since);

    // ---- One farmer ----

    @EntityGraph(attributePaths = "parcel")
    Page<PredictionRecord> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);

    @EntityGraph(attributePaths = "parcel")
    Page<PredictionRecord> findByUserIdAndTypeOrderByCreatedAtDesc(Long userId, PredictionType type, Pageable pageable);

    Optional<PredictionRecord> findFirstByUserIdAndTypeOrderByCreatedAtDesc(Long userId, PredictionType type);

    Optional<PredictionRecord> findFirstByUserIdAndParcelIdAndTypeOrderByCreatedAtDesc(Long userId, Long parcelId,
            PredictionType type);
}
