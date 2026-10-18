package tn.zitouna.ai.assistant.modules;

import java.time.ZoneId;
import java.util.List;
import java.util.Locale;

import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import tn.zitouna.ai.disease.DiseaseResult;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;

/**
 * maladie -> M1. M1 needs a leaf photo, which the chat cannot send yet: the chat uses the latest
 * diagnosis made on the "Diagnostic" page (from the history), if there is one.
 */
@Service
@RequiredArgsConstructor
public class DiseaseChatStub implements DiseaseService {

    private static final String ASK_PHOTO =
            "باش نعرف المرض، ابعثلي تصويرة واضحة لورقة من صفحة « Diagnostic ».";

    private static final String CHECK_WITH_TECHNICIAN = "استشير تقني فلاحي قبل ما تداوي.";

    private final HistoryService historyService;

    @Override
    public ModuleAnswer answer(ChatContext ctx) {
        // TODO(M1): when the chat accepts images, call DiseaseClient.predict(image) directly.
        Long parcelId = ctx.parcel() == null ? null : ctx.parcel().getId();
        var latest = historyService.latest(ctx.userId(), parcelId, PredictionType.DISEASE, DiseaseResult.class);
        if (latest.isEmpty()) {
            return ModuleAnswer.stub(ASK_PHOTO);
        }
        DiseaseResult d = latest.get().result();
        var date = latest.get().createdAt().atZone(ZoneId.of("Africa/Tunis")).toLocalDate();
        String reply = String.format(Locale.ROOT, "آخر تشخيص (%s): %s (%.0f%%). %s %s",
                date, diseaseName(d.label(), d.labelFr()), d.confidence() * 100, CHECK_WITH_TECHNICIAN, ASK_PHOTO);
        Fact fact = Fact.of("M1 (dernier diagnostic photo)", d.mock(),
                "date", date,
                "resultat", d.labelFr(),
                "confiance", Math.round(d.confidence() * 100) + " %",
                "conseil_de_traitement", d.advice(),
                "pour_un_nouveau_diagnostic", "envoyer une photo de feuille dans la page Diagnostic");
        return new ModuleAnswer(reply, d, d.mock(), List.of(fact));
    }

    /** M1 labels in Arabic for the template (the French label and advice go to the LLM as facts). */
    static String diseaseName(String label, String labelFr) {
        return switch (label) {
            case "healthy" -> "الورقة صحيحة";
            case "peacock_spot" -> "عين الطاووس";
            case "aculus_olearius" -> "أكاروس الزيتون";
            case "olive_knot" -> "سل الزيتون";
            default -> labelFr;
        };
    }
}
