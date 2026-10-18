package tn.zitouna.admin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import tn.zitouna.user.Role;
import tn.zitouna.user.User;
import tn.zitouna.user.UserRepository;

/**
 * The single admin account, from ADMIN_EMAIL / ADMIN_PASSWORD (.env), applied at every start-up:
 * <ul>
 * <li>the account is created if missing, or promoted to ADMIN if the email already exists;</li>
 * <li>ADMIN_PASSWORD (8 characters minimum), when set, is the admin password (changing it in .env changes it);</li>
 * <li>any other ADMIN account becomes FARMER: the platform has exactly one administrator.</li>
 * </ul>
 * Nothing happens if ADMIN_EMAIL is unset. Accounts created by /api/auth/register are always FARMER.
 */
@Component
public class AdminBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AdminBootstrap.class);
    private static final int MIN_PASSWORD_LENGTH = 8;

    private final UserRepository users;
    private final PasswordEncoder passwordEncoder;
    private final String email;
    private final String password;

    public AdminBootstrap(UserRepository users, PasswordEncoder passwordEncoder,
            @Value("${app.admin.email:}") String email, @Value("${app.admin.password:}") String password) {
        this.users = users;
        this.passwordEncoder = passwordEncoder;
        this.email = email == null ? "" : email.trim().toLowerCase();
        this.password = password == null ? "" : password;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        if (email.isBlank()) {
            return;
        }
        boolean validPassword = password.length() >= MIN_PASSWORD_LENGTH;
        if (!password.isEmpty() && !validPassword) {
            log.warn("ADMIN_PASSWORD shorter than {} characters: ignored", MIN_PASSWORD_LENGTH);
        }
        User admin = users.findByEmailIgnoreCase(email).orElse(null);
        if (admin == null) {
            if (!validPassword) {
                log.warn("ADMIN_PASSWORD missing: admin account {} not created", email);
                return;
            }
            admin = new User();
            admin.setFullName("Administrateur");
            admin.setEmail(email);
            log.info("Admin back-office: account {} created", email);
        }
        admin.setRole(Role.ADMIN);
        if (validPassword) {
            admin.setPasswordHash(passwordEncoder.encode(password));
        }
        users.save(admin);

        for (User other : users.findByRole(Role.ADMIN)) {
            if (!other.getEmail().equalsIgnoreCase(email)) {
                other.setRole(Role.FARMER);
                log.info("Admin back-office: {} is no longer ADMIN (single admin: {})", other.getEmail(), email);
            }
        }
    }
}
