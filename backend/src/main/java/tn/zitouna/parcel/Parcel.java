package tn.zitouna.parcel;

import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
import tn.zitouna.user.User;

/** An olive grove owned by a farmer. Its location feeds M2 (weather) and M3 (region). */
@Entity
@Table(name = "parcels")
@Getter
@Setter
@NoArgsConstructor
public class Parcel {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "owner_id")
    private User owner;

    @Column(nullable = false, length = 120)
    private String name;

    /** e.g. "Sfax", "Sousse", "Kairouan". Must match the names used by M3. */
    @Column(nullable = false, length = 60)
    private String governorate;

    @Column(nullable = false)
    private Double latitude;

    @Column(nullable = false)
    private Double longitude;

    private Double areaHa;

    /** Filled manually or by M6 (tree counting). */
    private Integer treeCount;

    /** e.g. "Chemlali", "Chetoui". */
    @Column(length = 60)
    private String variety;

    @Column(nullable = false)
    private boolean irrigated;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();
}
