package tn.zitouna.ai.irrigation;

import java.time.LocalDate;
import java.util.List;

import tn.zitouna.ai.AiResult;

/** Response of M2 POST /predict: daily water plan (ET0 from the LSTM, Open-Meteo weather) + frost/heatwave alerts. */
public record IrrigationResult(
        List<Day> days,
        List<Alert> alerts,
        String modelVersion,
        boolean mock) implements AiResult {

    /** waterNeedMm = ET0 x Kc - effective rain. litersPerTree is null when treeCount/area are unknown. */
    public record Day(LocalDate date, double et0Mm, double rainMm, double waterNeedMm, Double litersPerTree,
            boolean irrigate) {
    }

    /** type: FROST | HEATWAVE ; severity: LOW | MEDIUM | HIGH */
    public record Alert(LocalDate date, String type, String severity, String message) {
    }
}
