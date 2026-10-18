package tn.zitouna.admin;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;
import tn.zitouna.admin.AdminDtos.DailyCount;
import tn.zitouna.admin.AdminDtos.GovernorateCount;
import tn.zitouna.admin.AdminDtos.ParcelRow;
import tn.zitouna.admin.AdminDtos.PredictionRow;
import tn.zitouna.admin.AdminDtos.Stats;
import tn.zitouna.admin.AdminDtos.UserRow;
import tn.zitouna.common.ConflictException;
import tn.zitouna.common.NotFoundException;
import tn.zitouna.common.PageResponse;
import tn.zitouna.history.PredictionRecord;
import tn.zitouna.history.PredictionRepository;
import tn.zitouna.history.PredictionType;
import tn.zitouna.parcel.Parcel;
import tn.zitouna.parcel.ParcelRepository;
import tn.zitouna.status.StatusService;
import tn.zitouna.user.Role;
import tn.zitouna.user.User;
import tn.zitouna.user.UserRepository;

/** Back-office: read everything, manage accounts and parcels. Callers are checked by AdminController (ADMIN). */
@Service
@RequiredArgsConstructor
public class AdminService {

    private static final ZoneId TUNIS = ZoneId.of("Africa/Tunis");

    private final UserRepository users;
    private final ParcelRepository parcels;
    private final PredictionRepository predictions;
    private final StatusService statusService;

    @Transactional(readOnly = true)
    public Stats stats() {
        Map<PredictionType, Long> byType = new EnumMap<>(PredictionType.class);
        for (PredictionType type : PredictionType.values()) {
            byType.put(type, 0L);
        }
        for (Object[] row : predictions.countByType()) {
            byType.put((PredictionType) row[0], (Long) row[1]);
        }

        LocalDate today = LocalDate.now(TUNIS);
        Map<LocalDate, Long> perDay = new TreeMap<>();
        for (int i = 29; i >= 0; i--) {
            perDay.put(today.minusDays(i), 0L);
        }
        Instant since = today.minusDays(29).atStartOfDay(TUNIS).toInstant();
        for (Instant created : predictions.createdSince(since)) {
            perDay.merge(created.atZone(TUNIS).toLocalDate(), 1L, Long::sum);
        }
        List<DailyCount> last30Days = new ArrayList<>();
        perDay.forEach((date, count) -> last30Days.add(new DailyCount(date, count)));

        List<GovernorateCount> byGovernorate = parcels.countByGovernorate().stream()
                .map(row -> new GovernorateCount((String) row[0], (Long) row[1]))
                .toList();

        return new Stats(users.count(), users.countByRole(Role.ADMIN), parcels.count(), parcels.totalTrees(),
                parcels.totalAreaHa(), predictions.count(), predictions.countByMockTrue(), byType, last30Days,
                byGovernorate, statusService.status());
    }

    @Transactional(readOnly = true)
    public PageResponse<UserRow> users(String query, Pageable pageable) {
        return PageResponse.of(users.search(clean(query), pageable), u -> new UserRow(u.getId(), u.getFullName(),
                u.getEmail(), u.getRole(), u.getCreatedAt(), parcels.countByOwnerId(u.getId()),
                predictions.countByUserId(u.getId())));
    }

    /** Deletes a user account with its parcels and predictions (ON DELETE CASCADE). The admin cannot be deleted. */
    @Transactional
    public void deleteUser(Long adminId, Long userId) {
        User user = users.findById(userId).orElseThrow(() -> new NotFoundException("Utilisateur " + userId + " introuvable"));
        if (adminId.equals(userId) || user.getRole() == Role.ADMIN) {
            throw new ConflictException("Le compte administrateur ne peut pas être supprimé");
        }
        users.delete(user);
    }

    @Transactional(readOnly = true)
    public PageResponse<ParcelRow> parcels(String query, Pageable pageable) {
        return PageResponse.of(parcels.search(clean(query), pageable), AdminService::toRow);
    }

    @Transactional
    public void deleteParcel(Long parcelId) {
        if (!parcels.existsById(parcelId)) {
            throw new NotFoundException("Parcelle " + parcelId + " introuvable");
        }
        parcels.deleteById(parcelId);
    }

    @Transactional(readOnly = true)
    public PageResponse<PredictionRow> predictions(PredictionType type, Pageable pageable) {
        var page = type == null ? predictions.findAllByOrderByCreatedAtDesc(pageable)
                : predictions.findByTypeOrderByCreatedAtDesc(type, pageable);
        return PageResponse.of(page, AdminService::toRow);
    }

    private static ParcelRow toRow(Parcel p) {
        return new ParcelRow(p.getId(), p.getName(), p.getGovernorate(), p.getAreaHa(), p.getTreeCount(),
                p.getVariety(), p.isIrrigated(), p.getCreatedAt(), p.getOwner().getId(), p.getOwner().getFullName(),
                p.getOwner().getEmail());
    }

    private static PredictionRow toRow(PredictionRecord r) {
        return new PredictionRow(r.getId(), r.getType(), r.isMock(), r.getCreatedAt(), r.getUser().getId(),
                r.getUser().getEmail(), r.getParcel() == null ? null : r.getParcel().getId(),
                r.getParcel() == null ? null : r.getParcel().getName(), r.getRequestJson(), r.getResponseJson());
    }

    private static String clean(String query) {
        return query == null ? "" : query.trim();
    }
}
