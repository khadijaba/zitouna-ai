package tn.zitouna.ai.trees;

import java.util.Map;

import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import lombok.RequiredArgsConstructor;
import tn.zitouna.auth.CurrentUser;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;
import tn.zitouna.parcel.ParcelService;

@RestController
@RequestMapping("/api/parcels/{parcelId}")
@RequiredArgsConstructor
public class TreeCountController {

    private final TreeCountClient treeCountClient;
    private final ParcelService parcelService;
    private final HistoryService historyService;

    /** Counts the trees on a parcel image and saves the count on the parcel (real model only). */
    @PostMapping(value = "/count-trees", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public TreeCountResult countTrees(@AuthenticationPrincipal Jwt jwt, @PathVariable Long parcelId,
            @RequestPart("image") MultipartFile image) {
        Long userId = CurrentUser.id(jwt);
        parcelService.getOwned(userId, parcelId);
        TreeCountResult result = treeCountClient.count(image);
        if (!result.mock()) {
            parcelService.updateTreeCount(userId, parcelId, result.treeCount());
        }
        historyService.record(userId, parcelId, PredictionType.TREE_COUNT,
                Map.of("fileName", String.valueOf(image.getOriginalFilename())), result);
        return result;
    }
}
