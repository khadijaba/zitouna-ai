package tn.zitouna.parcel;

import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface ParcelRepository extends JpaRepository<Parcel, Long> {

    List<Parcel> findByOwnerIdOrderByCreatedAtDesc(Long ownerId);

    Optional<Parcel> findByIdAndOwnerId(Long id, Long ownerId);

    long countByOwnerId(Long ownerId);

    /** Admin back-office: parcel name, governorate or owner contains {@code q}, newest first. */
    @EntityGraph(attributePaths = "owner")
    @Query("""
            select p from Parcel p
            where :q = '' or lower(p.name) like lower(concat('%', :q, '%'))
                          or lower(p.governorate) like lower(concat('%', :q, '%'))
                          or lower(p.owner.email) like lower(concat('%', :q, '%'))
            order by p.createdAt desc""")
    Page<Parcel> search(String q, Pageable pageable);

    @Query("select coalesce(sum(p.treeCount), 0) from Parcel p")
    long totalTrees();

    @Query("select coalesce(sum(p.areaHa), 0) from Parcel p")
    double totalAreaHa();

    /** [governorate, number of parcels], most parcels first. */
    @Query("select p.governorate, count(p) from Parcel p group by p.governorate order by count(p) desc")
    List<Object[]> countByGovernorate();
}
