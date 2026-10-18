package tn.zitouna.ai.assistant.modules;

import java.util.List;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import tn.zitouna.ai.irrigation.IrrigationClient;
import tn.zitouna.ai.irrigation.IrrigationResult;

/** meteo_alerte -> M2 alerts. Uses the existing M2 client (still in mock mode until M2's model is ready). */
@Service
@RequiredArgsConstructor
public class WeatherChatService implements WeatherService {

    private final IrrigationClient irrigationClient;

    @Override
    public ModuleAnswer answer(ChatContext ctx) {
        var location = ctx.location().orElse(null);
        if (location == null) {
            return new ModuleAnswer(Replies.ASK_LOCATION, null, false);
        }
        IrrigationResult result = irrigationClient.predict(new IrrigationClient.Request(
                location.latitude(), location.longitude(), null, null, 7));

        String reply = result.alerts().isEmpty()
                ? "ما فماش حتى تنبيه (جليد ولا سخانة) في %s السبعة أيام الجايين.".formatted(location.label())
                : "رد بالك في %s: %s".formatted(location.label(), result.alerts().stream()
                        .map(a -> a.date() + ": " + alertName(a.type()))
                        .collect(Collectors.joining("، ")) + ".");
        Fact fact = Fact.of("M2", result.mock(),
                "lieu", location.label(),
                "alertes_7_jours", result.alerts().stream().map(a -> Fact.of("", false, "date", a.date(),
                        "type", a.type(), "gravite", a.severity(), "message", a.message()).data()).toList());
        return new ModuleAnswer(reply, result.alerts(), result.mock(), List.of(fact));
    }

    /** M2 alert messages are in French: the template names the alert from its type (the LLM gets the message). */
    static String alertName(String type) {
        return switch (type) {
            case "FROST" -> "خطر جليد";
            case "HEATWAVE" -> "سخانة قوية";
            default -> "تنبيه طقس";
        };
    }
}
