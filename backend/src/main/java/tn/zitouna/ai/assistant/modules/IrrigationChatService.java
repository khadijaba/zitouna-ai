package tn.zitouna.ai.assistant.modules;

import java.util.List;
import java.util.Locale;

import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import tn.zitouna.ai.irrigation.IrrigationClient;
import tn.zitouna.ai.irrigation.IrrigationResult;

/** irrigation -> M2. Uses the existing M2 client (still in mock mode until M2's model is ready). */
@Service
@RequiredArgsConstructor
public class IrrigationChatService implements IrrigationService {

    private final IrrigationClient irrigationClient;

    @Override
    public ModuleAnswer answer(ChatContext ctx) {
        var location = ctx.location().orElse(null);
        if (location == null) {
            return new ModuleAnswer(Replies.ASK_LOCATION, null, false);
        }
        Integer trees = ctx.parcel() != null ? ctx.parcel().getTreeCount() : null;
        Double area = ctx.parcel() != null ? ctx.parcel().getAreaHa() : null;
        IrrigationResult plan = irrigationClient.predict(new IrrigationClient.Request(
                location.latitude(), location.longitude(), trees, area, 7));

        long days = plan.days().stream().filter(IrrigationResult.Day::irrigate).count();
        double totalMm = plan.days().stream().mapToDouble(IrrigationResult.Day::waterNeedMm).sum();
        Double liters = plan.days().stream().filter(IrrigationResult.Day::irrigate)
                .map(IrrigationResult.Day::litersPerTree).filter(l -> l != null).findFirst().orElse(null);

        String reply = days == 0
                ? "في %s ما تستحقش تسقي السبعة أيام الجايين.".formatted(location.label())
                : String.format(Locale.ROOT, "في %s، السبعة أيام الجايين: لازمك تسقي %d مرات، الحاجة الكل ≈ %.0f مم%s.",
                        location.label(), days, totalMm,
                        liters == null ? "" : String.format(Locale.ROOT, " (≈ %.0f لتر للشجرة في كل مرة)", liters));
        Fact fact = Fact.of("M2", plan.mock(),
                "lieu", location.label(),
                "jours_irrigation_sur_7", days,
                "besoin_total_mm", Math.round(totalMm * 10) / 10.0,
                "litres_par_arbre_par_irrigation", liters,
                "jours", plan.days().stream().map(d -> Fact.of("", false, "date", d.date(), "besoin_mm",
                        d.waterNeedMm(), "pluie_mm", d.rainMm(), "irriguer", d.irrigate()).data()).toList(),
                "alertes", plan.alerts().stream().map(a -> Fact.of("", false, "date", a.date(), "type", a.type(),
                        "message", a.message()).data()).toList());
        return new ModuleAnswer(reply, plan, plan.mock(), List.of(fact));
    }
}
