package tn.zitouna.ai.assistant;

import java.util.List;

import tn.zitouna.ai.AiResult;

/**
 * Response of M5 POST /intent. When {@code clarify} is true, {@code intent} is still the best
 * guess and {@code question} is what to ask the farmer.
 */
public record IntentResponse(
        Intent intent,
        double confidence,
        boolean clarify,
        String question,
        List<Candidate> candidates,
        boolean modelsAgree,
        Entities entities,
        String modelVersion,
        boolean mock) implements AiResult {

    public static final String GENERIC_QUESTION =
            "ما فهمتكش مليح. سؤالك على المرض، السقي، الطقس، الصابة، السوم ولا عدد الزيتون؟";

    public record Candidate(Intent intent, double score) {
    }

    /** gouvernorat: canonical id such as "beja" or "sidi bouzid", or null. */
    public record Entities(String gouvernorat) {
    }

    /** Used when M5 is down or too slow: ask the generic question instead of failing the chat. */
    public static IntentResponse fallback() {
        List<Candidate> topics = List.of(Intent.MALADIE, Intent.IRRIGATION, Intent.METEO_ALERTE, Intent.RECOLTE,
                Intent.PRIX_VENTE, Intent.COMPTAGE).stream().map(i -> new Candidate(i, 0)).toList();
        return new IntentResponse(Intent.CONSEIL_GENERAL, 0, true, GENERIC_QUESTION, topics, false,
                new Entities(null), "fallback", true);
    }

    /** The farmer picked an intent from the suggestion buttons: no classification needed. */
    public static IntentResponse forced(Intent intent) {
        return new IntentResponse(intent, 1, false, null, List.of(new Candidate(intent, 1)), true,
                new Entities(null), "forced", false);
    }
}
