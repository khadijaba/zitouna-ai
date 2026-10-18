package tn.zitouna.user;

public record UserDto(Long id, String fullName, String email, Role role) {

    public static UserDto from(User user) {
        return new UserDto(user.getId(), user.getFullName(), user.getEmail(), user.getRole());
    }
}
