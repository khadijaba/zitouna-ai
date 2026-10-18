package tn.zitouna.parcel;

import java.time.Instant;

public record ParcelDto(
        Long id,
        String name,
        String governorate,
        Double latitude,
        Double longitude,
        Double areaHa,
        Integer treeCount,
        String variety,
        boolean irrigated,
        Instant createdAt) {

    public static ParcelDto from(Parcel p) {
        return new ParcelDto(p.getId(), p.getName(), p.getGovernorate(), p.getLatitude(), p.getLongitude(),
                p.getAreaHa(), p.getTreeCount(), p.getVariety(), p.isIrrigated(), p.getCreatedAt());
    }
}
