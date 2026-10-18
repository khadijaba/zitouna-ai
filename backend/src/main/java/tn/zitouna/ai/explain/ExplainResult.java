package tn.zitouna.ai.explain;

import tn.zitouna.ai.AiResult;

/**
 * Response of M5 POST /explain. {@code fallback}: no LLM answered, the explanation is a template sentence
 * built from the real figures (so it is not demo data: {@code mock} is always false).
 */
public record ExplainResult(String explanation, String provider, String model, long latencyMs, boolean fallback)
        implements AiResult {

    @Override
    public boolean mock() {
        return false;
    }
}
