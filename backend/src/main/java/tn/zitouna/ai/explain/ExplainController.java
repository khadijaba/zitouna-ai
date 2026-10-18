package tn.zitouna.ai.explain;

import java.util.Map;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import tn.zitouna.auth.CurrentUser;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;

/** « Expliquer avec l'IA » button of every module: the LLM explains the result shown to the farmer. */
@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class ExplainController {

    private final ExplainClient explainClient;
    private final HistoryService historyService;

    @PostMapping("/explain")
    public ExplainResult explain(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody ExplainRequest request) {
        ExplainResult result = explainClient.explain(request);
        historyService.record(CurrentUser.id(jwt), null, PredictionType.EXPLAIN,
                Map.of("module", request.module(), "language", request.languageOrDefault()), result);
        return result;
    }
}
