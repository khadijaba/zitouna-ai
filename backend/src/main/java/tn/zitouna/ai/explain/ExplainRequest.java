package tn.zitouna.ai.explain;

import java.util.Map;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

/**
 * Body of POST /api/ai/explain: the result a module just returned (as displayed by the frontend),
 * and the language of the explanation ("fr" by default, or "derja").
 */
public record ExplainRequest(
        @NotNull @Pattern(regexp = "M[1-6]", message = "module doit valoir M1 à M6") String module,
        @NotNull Map<String, Object> result,
        @Pattern(regexp = "fr|derja", message = "language doit valoir fr ou derja") String language) {

    public String languageOrDefault() {
        return language == null ? "fr" : language;
    }
}
