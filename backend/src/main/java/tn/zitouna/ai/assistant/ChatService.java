package tn.zitouna.ai.assistant;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import tn.zitouna.ai.AiServiceException;
import tn.zitouna.ai.assistant.modules.ChatContext;
import tn.zitouna.ai.assistant.modules.DiseaseService;
import tn.zitouna.ai.assistant.modules.Fact;
import tn.zitouna.ai.assistant.modules.IrrigationService;
import tn.zitouna.ai.assistant.modules.ModuleAnswer;
import tn.zitouna.ai.assistant.modules.PriceService;
import tn.zitouna.ai.assistant.modules.RagService;
import tn.zitouna.ai.assistant.modules.TreeCountService;
import tn.zitouna.ai.assistant.modules.WeatherService;
import tn.zitouna.ai.assistant.modules.YieldService;
import tn.zitouna.history.HistoryService;
import tn.zitouna.history.PredictionType;
import tn.zitouna.parcel.Parcel;
import tn.zitouna.parcel.ParcelService;

/**
 * Chat orchestration:
 * 1. M5 detects the intent (or asks to clarify);
 * 2. the module(s) that can answer are called, plus complementary ones (harvest -> also price...);
 * 3. an LLM (M5 /answer) writes the reply from their facts; if no LLM answers, the template reply is used.
 * A module failure never breaks the chat: the farmer gets a "try again" reply.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    // Replies are always Tunisian derja in Arabic script, whatever the script of the question.
    static final String GREETING = "عسلامة! نعرف نعاونك في مرض الزيتون، السقي، الطقس، الصابة، "
            + "السوم وعدد الزيتون. شنوة سؤالك؟";
    static final String OFF_TOPIC = "سامحني، أنا نعاون كان في فلاحة الزيتون. "
            + "جرّب مثلا: «قداش نسقي زيتوني الجمعة هاذي؟»";
    static final String MODULE_DOWN = "سامحني، ما نجمتش نجاوبك توا. عاود بعد شوية.";

    /** Complementary modules whose facts enrich the answer (their failure is ignored). */
    static final Map<Intent, List<Intent>> ENRICH = Map.of(
            Intent.METEO_ALERTE, List.of(Intent.IRRIGATION),
            Intent.RECOLTE, List.of(Intent.PRIX_VENTE),
            Intent.PRIX_VENTE, List.of(Intent.RECOLTE));

    private final IntentClient intentClient;
    private final AnswerClient answerClient;
    private final ParcelService parcelService;
    private final HistoryService historyService;
    private final DiseaseService diseaseService;
    private final IrrigationService irrigationService;
    private final WeatherService weatherService;
    private final YieldService yieldService;
    private final PriceService priceService;
    private final TreeCountService treeCountService;
    private final RagService ragService;

    public ChatResponse chat(Long userId, ChatRequest request) {
        Parcel parcel = request.parcelId() == null ? null : parcelService.getOwned(userId, request.parcelId());
        IntentResponse nlu = request.forcedIntent() != null
                ? IntentResponse.forced(request.forcedIntent())
                : intentClient.detect(request.text());

        ChatResponse response = nlu.clarify()
                ? new ChatResponse(nlu.question(), nlu.intent(), true, suggestions(nlu), null, nlu.mock(),
                        ChatResponse.TEMPLATE)
                : route(nlu, new ChatContext(userId, request.text(), parcel, governorate(nlu)));

        historyService.record(userId, request.parcelId(), PredictionType.CHAT, request, response);
        return response;
    }

    private ChatResponse route(IntentResponse nlu, ChatContext ctx) {
        Intent intent = nlu.intent();
        if (intent == Intent.SALUTATION || intent == Intent.HORS_SUJET) {
            // Fixed, instant answers: no module, no LLM.
            return answer(intent, intent == Intent.SALUTATION ? GREETING : OFF_TOPIC, null, false, ChatResponse.TEMPLATE);
        }
        ModuleAnswer module;
        try {
            module = call(intent, ctx);
        } catch (AiServiceException e) {
            log.warn("Module for intent {} failed: {}", intent, e.getMessage());
            return answer(intent, MODULE_DOWN, null, nlu.mock(), ChatResponse.TEMPLATE);
        }

        List<Fact> facts = new ArrayList<>(module.facts());
        boolean mock = nlu.mock() || module.mock();
        for (Intent extra : ENRICH.getOrDefault(intent, List.of())) {
            try {
                ModuleAnswer more = call(extra, ctx);
                if (more != null && !more.facts().isEmpty()) {
                    facts.addAll(more.facts());
                    mock |= more.mock();
                }
            } catch (AiServiceException e) {
                log.info("Complementary module {} skipped: {}", extra, e.getMessage());
            }
        }

        var llm = answerClient.answer(new AnswerClient.Request(ctx.text(), intent, facts, parcelInfo(ctx), module.reply()));
        return llm.isPresent()
                ? answer(intent, llm.get().answer(), module.data(), mock, llm.get().generatedBy())
                : answer(intent, module.reply(), module.data(), mock, ChatResponse.TEMPLATE);
    }

    private ModuleAnswer call(Intent intent, ChatContext ctx) {
        return switch (intent) {
            case MALADIE -> diseaseService.answer(ctx);
            case IRRIGATION -> irrigationService.answer(ctx);
            case METEO_ALERTE -> weatherService.answer(ctx);
            case RECOLTE -> yieldService.answer(ctx);
            case PRIX_VENTE -> priceService.answer(ctx);
            case COMPTAGE -> treeCountService.answer(ctx);
            case CONSEIL_GENERAL -> ragService.answer(ctx);
            case SALUTATION, HORS_SUJET -> throw new IllegalArgumentException("no module for " + intent);
        };
    }

    private static ChatResponse answer(Intent intent, String reply, Object data, boolean mock, String generatedBy) {
        return new ChatResponse(reply, intent, false, List.of(), data, mock, generatedBy);
    }

    private static AnswerClient.Parcel parcelInfo(ChatContext ctx) {
        Parcel p = ctx.parcel();
        return p == null ? null
                : new AnswerClient.Parcel(p.getName(), p.getGovernorate(), p.getTreeCount(), p.getAreaHa(),
                        p.getVariety(), p.isIrrigated());
    }

    /**
     * Candidate intents become buttons; greetings and off-topic make no sense as buttons.
     * With fewer than 2 left (e.g. the domain guard fired on "hors_sujet"), the main topics are added.
     */
    private static List<Intent> suggestions(IntentResponse nlu) {
        List<Intent> intents = nlu.candidates() == null ? List.of()
                : nlu.candidates().stream().map(IntentResponse.Candidate::intent).filter(Intent::isSuggestable).toList();
        if (intents.size() >= 2) {
            return intents;
        }
        Set<Intent> padded = new LinkedHashSet<>(intents);
        IntentResponse.fallback().candidates().forEach(c -> padded.add(c.intent()));
        return List.copyOf(padded);
    }

    private static String governorate(IntentResponse nlu) {
        return nlu.entities() == null ? null : nlu.entities().gouvernorat();
    }
}
