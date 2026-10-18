package tn.zitouna.ai.assistant.modules;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * A compact piece of module output given to the LLM (M5 /answer) to write the reply.
 * Keep data small and readable: the LLM only sees these values, it must not invent others.
 *
 * @param source module that produced it ("M2", "M3", "M1 (historique)"...)
 * @param mock   true while the module returns placeholder data
 */
public record Fact(String source, boolean mock, Map<String, Object> data) {

    /** Builds data from key/value pairs, skipping null values: of("M3", true, "kg", 7500, "min", null). */
    public static Fact of(String source, boolean mock, Object... keyValues) {
        Map<String, Object> data = new LinkedHashMap<>();
        for (int i = 0; i + 1 < keyValues.length; i += 2) {
            if (keyValues[i + 1] != null) {
                data.put((String) keyValues[i], keyValues[i + 1]);
            }
        }
        return new Fact(source, mock, data);
    }
}
