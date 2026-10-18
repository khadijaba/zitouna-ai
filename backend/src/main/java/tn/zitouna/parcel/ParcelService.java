package tn.zitouna.parcel;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;
import tn.zitouna.common.NotFoundException;
import tn.zitouna.user.UserRepository;

@Service
@RequiredArgsConstructor
public class ParcelService {

    private final ParcelRepository parcels;
    private final UserRepository users;

    @Transactional(readOnly = true)
    public List<ParcelDto> list(Long userId) {
        return parcels.findByOwnerIdOrderByCreatedAtDesc(userId).stream().map(ParcelDto::from).toList();
    }

    /** Returns the parcel only if it belongs to the user, so nobody can read someone else's parcel. */
    @Transactional(readOnly = true)
    public Parcel getOwned(Long userId, Long parcelId) {
        return parcels.findByIdAndOwnerId(parcelId, userId)
                .orElseThrow(() -> new NotFoundException("Parcel " + parcelId + " not found"));
    }

    @Transactional
    public ParcelDto create(Long userId, ParcelRequest request) {
        Parcel parcel = new Parcel();
        parcel.setOwner(users.getReferenceById(userId));
        apply(parcel, request);
        return ParcelDto.from(parcels.save(parcel));
    }

    @Transactional
    public ParcelDto update(Long userId, Long parcelId, ParcelRequest request) {
        Parcel parcel = getOwned(userId, parcelId);
        apply(parcel, request);
        return ParcelDto.from(parcel);
    }

    @Transactional
    public void delete(Long userId, Long parcelId) {
        parcels.delete(getOwned(userId, parcelId));
    }

    @Transactional
    public void updateTreeCount(Long userId, Long parcelId, int treeCount) {
        getOwned(userId, parcelId).setTreeCount(treeCount);
    }

    private static void apply(Parcel parcel, ParcelRequest r) {
        parcel.setName(r.name().trim());
        parcel.setGovernorate(r.governorate().trim());
        parcel.setLatitude(r.latitude());
        parcel.setLongitude(r.longitude());
        parcel.setAreaHa(r.areaHa());
        parcel.setTreeCount(r.treeCount());
        parcel.setVariety(r.variety());
        parcel.setIrrigated(r.irrigated());
    }
}
