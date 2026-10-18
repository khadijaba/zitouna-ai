package tn.zitouna.auth;

import org.springframework.security.oauth2.jwt.Jwt;

/** The JWT subject is the user id. Use with {@code @AuthenticationPrincipal Jwt jwt} in controllers. */
public final class CurrentUser {

    private CurrentUser() {
    }

    public static Long id(Jwt jwt) {
        return Long.valueOf(jwt.getSubject());
    }
}
