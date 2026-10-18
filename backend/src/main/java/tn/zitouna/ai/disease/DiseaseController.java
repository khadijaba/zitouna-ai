package tn.zitouna.ai.disease;

import java.util.Map;

import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import lombok.RequiredArgsConstructor;
import tn.zitouna.auth.CurrentUser;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;
import tn.zitouna.parcel.ParcelService;

@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class DiseaseController {

    private final DiseaseClient diseaseClient;
    private final ParcelService parcelService;
    private final HistoryService historyService;

    /** Leaf photo -> disease + treatment advice. Optionally linked to a parcel for the history. */
    @PostMapping(value = "/disease", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public DiseaseResult diagnose(@AuthenticationPrincipal Jwt jwt,
            @RequestPart("image") MultipartFile image,
            @RequestParam(required = false) Long parcelId) {
        Long userId = CurrentUser.id(jwt);
        if (parcelId != null) {
            parcelService.getOwned(userId, parcelId);
        }
        DiseaseResult result = diseaseClient.predict(image);
        historyService.record(userId, parcelId, PredictionType.DISEASE,
                Map.of("fileName", String.valueOf(image.getOriginalFilename())), result);
        return result;
    }
}
