package tn.zitouna.admin;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonRawValue;

import tn.zitouna.history.PredictionType;
import tn.zitouna.status.StatusResponse;
import tn.zitouna.user.Role;

/** JSON shapes of the admin back-office API (/api/admin/**). */
public final class AdminDtos {

    private AdminDtos() {
    }

    /** Dashboard: totals, activity of the last 30 days, live state of the six AI services. */
    public record Stats(
            long users,
            long admins,
            long parcels,
            long trees,
            double areaHa,
            long predictions,
            long mockPredictions,
            Map<PredictionType, Long> predictionsByType,
            List<DailyCount> last30Days,
            List<GovernorateCount> parcelsByGovernorate,
            StatusResponse status) {
    }

    public record DailyCount(LocalDate date, long count) {
    }

    public record GovernorateCount(String governorate, long parcels) {
    }

    public record UserRow(Long id, String fullName, String email, Role role, Instant createdAt, long parcels,
            long predictions) {
    }

    public record ParcelRow(Long id, String name, String governorate, Double areaHa, Integer treeCount,
            String variety, boolean irrigated, Instant createdAt, Long ownerId, String ownerName, String ownerEmail) {
    }

    public record PredictionRow(Long id, PredictionType type, boolean mock, Instant createdAt, Long userId,
            String userEmail, Long parcelId, String parcelName, @JsonRawValue String request,
            @JsonRawValue String response) {
    }
}
