package tn.zitouna.user;

import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByEmailIgnoreCase(String email);

    boolean existsByEmailIgnoreCase(String email);

    long countByRole(Role role);

    List<User> findByRole(Role role);

    /** Admin back-office: name or email contains {@code q} (empty = everyone), newest first. */
    @Query("""
            select u from User u
            where :q = '' or lower(u.fullName) like lower(concat('%', :q, '%'))
                          or lower(u.email) like lower(concat('%', :q, '%'))
            order by u.createdAt desc""")
    Page<User> search(String q, Pageable pageable);
}
