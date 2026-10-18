package tn.zitouna.history;

import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import tn.zitouna.parcel.Parcel;
import tn.zitouna.user.User;

/** One call to an AI module, kept so the farmer can see past diagnoses, forecasts and advice. */
@Entity
@Table(name = "predictions")
@Getter
@Setter
@NoArgsConstructor
public class PredictionRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id")
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parcel_id")
    private Parcel parcel;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private PredictionType type;

    @Column(columnDefinition = "TEXT")
    private String requestJson;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String responseJson;

    @Column(nullable = false)
    private boolean mock;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();
}
