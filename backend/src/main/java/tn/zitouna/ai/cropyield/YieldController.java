package tn.zitouna.ai.cropyield;

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
public class YieldController {

    private final YieldClient yieldClient;
    private final ParcelService parcelService;
    private final HistoryService historyService;

    @GetMapping("/yield")
    public YieldResult yieldForecast(@AuthenticationPrincipal Jwt jwt, @PathVariable Long parcelId,
            @RequestParam(required = false) Integer season) {
        Long userId = CurrentUser.id(jwt);
        Parcel parcel = parcelService.getOwned(userId, parcelId);
        var request = new YieldClient.Request(parcel.getGovernorate(),
                season != null ? season : YieldClient.currentSeason(), parcel.getTreeCount(), parcel.getAreaHa());
        YieldResult result = yieldClient.predict(request);
        historyService.record(userId, parcelId, PredictionType.YIELD, request, result);
        return result;
    }
}
