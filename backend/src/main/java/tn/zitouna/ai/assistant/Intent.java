package tn.zitouna.ai.assistant;

import com.fasterxml.jackson.annotation.JsonProperty;

/** The 9 intents detected by M5. JSON values are the labels of the trained model. */
public enum Intent {
    @JsonProperty("maladie") MALADIE,                  // -> M1
    @JsonProperty("irrigation") IRRIGATION,            // -> M2 (water need)
    @JsonProperty("meteo_alerte") METEO_ALERTE,        // -> M2 (weather alerts)
    @JsonProperty("recolte") RECOLTE,                  // -> M3
    @JsonProperty("prix_vente") PRIX_VENTE,            // -> M4
    @JsonProperty("comptage") COMPTAGE,                // -> M6
    @JsonProperty("conseil_general") CONSEIL_GENERAL,  // -> RAG (M5)
    @JsonProperty("salutation") SALUTATION,            // fixed answer
    @JsonProperty("hors_sujet") HORS_SUJET;            // polite refusal

    /** Intents worth offering as buttons when the assistant asks for clarification. */
    public boolean isSuggestable() {
        return this != SALUTATION && this != HORS_SUJET;
    }
}
