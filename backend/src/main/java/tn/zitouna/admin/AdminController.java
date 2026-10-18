package tn.zitouna.admin;

import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import tn.zitouna.admin.AdminDtos.ParcelRow;
import tn.zitouna.admin.AdminDtos.PredictionRow;
import tn.zitouna.admin.AdminDtos.Stats;
import tn.zitouna.admin.AdminDtos.UserRow;
import tn.zitouna.auth.CurrentUser;
import tn.zitouna.common.PageResponse;
import tn.zitouna.history.PredictionType;

/**
 * Back-office API. Every endpoint needs a JWT with the ADMIN role (403 otherwise). There is exactly one admin,
 * defined in .env (AdminBootstrap): roles cannot be changed from here.
 */
@RestController
@RequestMapping("/api/admin")
@PreAuthorize("hasRole('ADMIN')")
@RequiredArgsConstructor
public class AdminController {

    private final AdminService adminService;

    @GetMapping("/stats")
    public Stats stats() {
        return adminService.stats();
    }

    @GetMapping("/users")
    public PageResponse<UserRow> users(@RequestParam(defaultValue = "") String q,
            @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        return adminService.users(q, pageable(page, size));
    }

    @DeleteMapping("/users/{id}")
    public ResponseEntity<Void> deleteUser(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id) {
        adminService.deleteUser(CurrentUser.id(jwt), id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/parcels")
    public PageResponse<ParcelRow> parcels(@RequestParam(defaultValue = "") String q,
            @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        return adminService.parcels(q, pageable(page, size));
    }

    @DeleteMapping("/parcels/{id}")
    public ResponseEntity<Void> deleteParcel(@PathVariable Long id) {
        adminService.deleteParcel(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/predictions")
    public PageResponse<PredictionRow> predictions(@RequestParam(required = false) PredictionType type,
            @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        return adminService.predictions(type, pageable(page, size));
    }

    private static PageRequest pageable(int page, int size) {
        return PageRequest.of(Math.max(page, 0), Math.clamp(size, 1, 100));
    }
}
