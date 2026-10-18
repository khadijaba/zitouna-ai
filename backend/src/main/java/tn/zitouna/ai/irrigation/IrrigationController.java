package tn.zitouna.ai.irrigation;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import tn.zitouna.auth.CurrentUser;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;
import tn.zitouna.parcel.Parcel;
import tn.zitouna.parcel.ParcelService;

@RestController
@RequestMapping("/api/parcels/{parcelId}")
@RequiredArgsConstructor
public class IrrigationController {

    /** Open-Meteo forecasts (and the M2 model) go up to 16 days. */
    static final int MAX_DAYS = 16;

    private final IrrigationClient irrigationClient;
    private final ParcelService parcelService;
    private final HistoryService historyService;

    /** Irrigation plan (7 days by default, up to 16) and weather alerts for the parcel's location. */
    @GetMapping("/irrigation")
    public IrrigationResult irrigation(@AuthenticationPrincipal Jwt jwt, @PathVariable Long parcelId,
            @RequestParam(defaultValue = "7") int days) {
        Long userId = CurrentUser.id(jwt);
        Parcel parcel = parcelService.getOwned(userId, parcelId);
        var request = new IrrigationClient.Request(parcel.getLatitude(), parcel.getLongitude(),
                parcel.getTreeCount(), parcel.getAreaHa(), Math.clamp(days, 1, MAX_DAYS));
        IrrigationResult result = irrigationClient.predict(request);
        historyService.record(userId, parcelId, PredictionType.IRRIGATION, request, result);
        return result;
    }
}
