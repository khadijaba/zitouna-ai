package tn.zitouna.ai.assistant.modules;

import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/** The 24 governorates, keyed by the ids returned by M5 (entities.gouvernorat): capital coordinates, Arabic name. */
final class Governorates {

    private record Info(double latitude, double longitude, String arabic) {
    }

    private static final Map<String, Info> GOVERNORATES = Map.ofEntries(
            Map.entry("ariana", new Info(36.86, 10.19, "أريانة")),
            Map.entry("beja", new Info(36.73, 9.18, "باجة")),
            Map.entry("ben arous", new Info(36.75, 10.22, "بن عروس")),
            Map.entry("bizerte", new Info(37.27, 9.87, "بنزرت")),
            Map.entry("gabes", new Info(33.88, 10.10, "قابس")),
            Map.entry("gafsa", new Info(34.42, 8.78, "قفصة")),
            Map.entry("jendouba", new Info(36.50, 8.78, "جندوبة")),
            Map.entry("kairouan", new Info(35.68, 10.10, "القيروان")),
            Map.entry("kasserine", new Info(35.17, 8.83, "القصرين")),
            Map.entry("kebili", new Info(33.70, 8.97, "قبلي")),
            Map.entry("kef", new Info(36.18, 8.71, "الكاف")),
            Map.entry("mahdia", new Info(35.50, 11.06, "المهدية")),
            Map.entry("manouba", new Info(36.81, 10.10, "منوبة")),
            Map.entry("medenine", new Info(33.35, 10.50, "مدنين")),
            Map.entry("monastir", new Info(35.78, 10.83, "المنستير")),
            Map.entry("nabeul", new Info(36.45, 10.73, "نابل")),
            Map.entry("sfax", new Info(34.74, 10.76, "صفاقس")),
            Map.entry("sidi bouzid", new Info(35.04, 9.48, "سيدي بوزيد")),
            Map.entry("siliana", new Info(36.08, 9.37, "سليانة")),
            Map.entry("sousse", new Info(35.83, 10.64, "سوسة")),
            Map.entry("tataouine", new Info(32.93, 10.45, "تطاوين")),
            Map.entry("tozeur", new Info(33.92, 8.13, "توزر")),
            Map.entry("tunis", new Info(36.81, 10.18, "تونس")),
            Map.entry("zaghouan", new Info(36.40, 10.14, "زغوان")));

    private Governorates() {
    }

    /** [latitude, longitude], or empty for an unknown / null id. */
    static Optional<double[]> coordinates(String governorate) {
        return find(governorate).map(g -> new double[] { g.latitude(), g.longitude() });
    }

    /** "sfax" or "Sfax" -> "صفاقس"; an unknown name is returned unchanged. */
    static String arabic(String governorate) {
        return find(governorate).map(Info::arabic).orElse(governorate);
    }

    private static Optional<Info> find(String governorate) {
        return governorate == null ? Optional.empty()
                : Optional.ofNullable(GOVERNORATES.get(governorate.trim().toLowerCase(Locale.ROOT)));
    }
}
