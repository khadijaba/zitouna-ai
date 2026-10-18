package tn.zitouna.ai.assistant.modules;

import java.util.Optional;

import tn.zitouna.parcel.Parcel;

/**
 * What a module needs to answer a chat question.
 *
 * @param parcel      the parcel selected in the chat, or null
 * @param governorate governorate detected by M5 in the question ("beja", "sidi bouzid"...), or null
 */
public record ChatContext(Long userId, String text, Parcel parcel, String governorate) {

    /** Where the question is about: the selected parcel first, else the governorate cited in the text. */
    public Optional<Location> location() {
        if (parcel != null) {
            return Optional.of(new Location(parcel.getName(), parcel.getGovernorate(),
                    parcel.getLatitude(), parcel.getLongitude()));
        }
        return Governorates.coordinates(governorate)
                .map(c -> new Location(Governorates.arabic(governorate), governorate, c[0], c[1]));
    }

    /** label: shown in replies (parcel name, or Arabic governorate name); governorate: id sent to the modules. */
    public record Location(String label, String governorate, double latitude, double longitude) {
    }
}
