package tn.zitouna.ai.price;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import tn.zitouna.auth.CurrentUser;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;

@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class PriceController {

    private final PriceClient priceClient;
    private final HistoryService historyService;

    @GetMapping("/price")
    public PriceResult price(@AuthenticationPrincipal Jwt jwt,
            @RequestParam(defaultValue = "8") int horizonWeeks,
            @RequestParam(required = false) Double quantityKg) {
        var request = new PriceClient.Request(Math.clamp(horizonWeeks, 1, 26), quantityKg);
        PriceResult result = priceClient.predict(request);
        historyService.record(CurrentUser.id(jwt), null, PredictionType.PRICE, request, result);
        return result;
    }
}
