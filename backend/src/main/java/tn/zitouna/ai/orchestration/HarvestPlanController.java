package tn.zitouna.ai.orchestration;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import lombok.RequiredArgsConstructor;
import tn.zitouna.auth.CurrentUser;

@RestController
@RequestMapping("/api/parcels/{parcelId}")
@RequiredArgsConstructor
public class HarvestPlanController {

    private final HarvestPlanService harvestPlanService;

    /** Multipart with an optional "image" field. Without image, the parcel's saved tree count is used. */
    @PostMapping("/harvest-plan")
    public HarvestPlan harvestPlan(@AuthenticationPrincipal Jwt jwt, @PathVariable Long parcelId,
            @RequestParam(value = "image", required = false) MultipartFile image) {
        return harvestPlanService.plan(CurrentUser.id(jwt), parcelId, image);
    }
}
