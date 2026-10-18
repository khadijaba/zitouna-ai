package tn.zitouna.ai;

/**
 * Every AI service response carries {@code mock}: true while the module still returns
 * placeholder data (no trained model loaded yet). The UI shows a "demo data" badge.
 */
public interface AiResult {

    boolean mock();
}
