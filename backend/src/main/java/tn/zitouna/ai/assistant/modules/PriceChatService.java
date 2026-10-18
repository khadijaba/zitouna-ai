package tn.zitouna.ai.assistant.modules;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;

import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import tn.zitouna.ai.price.PriceClient;
import tn.zitouna.ai.price.PriceResult;

/** prix_vente -> M4. Uses the existing M4 client (still in mock mode until M4's model is ready). */
@Service
@RequiredArgsConstructor
public class PriceChatService implements PriceService {

    private final PriceClient priceClient;

    @Override
    public ModuleAnswer answer(ChatContext ctx) {
        PriceResult price = priceClient.predict(new PriceClient.Request(8, null));
        double today = price.history().isEmpty() ? 0 : price.history().getLast().price();
        String advice = PriceResult.SELL_NOW.equals(price.recommendation())
                ? "ننصحك تبيع توا."
                : "ننصحك تخزن زيتك وتستنى شوية.";
        // price.reason() is in French: it goes to the LLM as a fact, not in the template.
        String reply = String.format(Locale.ROOT, "سوم الزيت اليوم ≈ %.2f %s. %s",
                today, perUnit(price.currency(), price.unit()), advice);
        var best = price.forecast().stream().max(Comparator.comparingDouble(PriceResult.Point::price)).orElse(null);
        Fact fact = Fact.of("M4", price.mock(),
                "prix_huile_aujourdhui_tnd_kg", today,
                "prix_max_prevu_tnd_kg", best == null ? null : best.price(),
                "date_prix_max", best == null ? null : best.date(),
                "conseil", price.recommendation(),
                "explication", price.reason());
        return new ModuleAnswer(reply, price, price.mock(), List.of(fact));
    }

    /** "TND", "kg" -> "دينار للكيلو"; other units are kept as M4 sends them. */
    static String perUnit(String currency, String unit) {
        String c = "TND".equalsIgnoreCase(currency) ? "دينار" : currency;
        return "kg".equalsIgnoreCase(unit) ? c + " للكيلو" : c + "/" + unit;
    }
}
