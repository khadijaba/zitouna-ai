package tn.zitouna.ai.price;

import java.time.LocalDate;
import java.util.List;

import tn.zitouna.ai.AiResult;

/**
 * Response of M4 POST /predict. Olive-oil prices in TND per kg of oil: {@code history} = last observed
 * monthly prices, {@code forecast} = one point per week from today with an 80 % interval.
 * {@code source} says where the prices come from (null in mock mode).
 */
public record PriceResult(
        String currency,
        String unit,
        List<Point> history,
        List<Point> forecast,
        String recommendation,
        String reason,
        Double expectedGainTnd,
        String modelVersion,
        boolean mock,
        String source) implements AiResult {

    public static final String SELL_NOW = "SELL_NOW";
    public static final String STORE = "STORE";

    /** low/high: prediction interval, null for historical points. */
    public record Point(LocalDate date, double price, Double low, Double high) {
    }
}
