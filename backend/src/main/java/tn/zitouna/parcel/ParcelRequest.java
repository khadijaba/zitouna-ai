package tn.zitouna.parcel;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

public record ParcelRequest(
        @NotBlank @Size(max = 120) String name,
        @NotBlank @Size(max = 60) String governorate,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double latitude,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double longitude,
        @Positive Double areaHa,
        @PositiveOrZero Integer treeCount,
        @Size(max = 60) String variety,
        boolean irrigated) {
}
