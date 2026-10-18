package tn.zitouna.auth.dto;

import java.time.Instant;

import tn.zitouna.user.UserDto;

public record AuthResponse(String token, Instant expiresAt, UserDto user) {
}
