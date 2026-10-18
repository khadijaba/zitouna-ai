package tn.zitouna.ai.assistant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;

import tn.zitouna.ai.AiServiceException;
import tn.zitouna.ai.assistant.IntentResponse.Candidate;
import tn.zitouna.ai.assistant.IntentResponse.Entities;
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
import tn.zitouna.parcel.ParcelService;

@ExtendWith(MockitoExtension.class)
class ChatServiceTest {

    private static final long USER = 7L;

    @Mock IntentClient intentClient;
    @Mock AnswerClient answerClient;
    @Mock ParcelService parcelService;
    @Mock HistoryService historyService;
    @Mock DiseaseService diseaseService;
    @Mock IrrigationService irrigationService;
    @Mock WeatherService weatherService;
    @Mock YieldService yieldService;
    @Mock PriceService priceService;
    @Mock TreeCountService treeCountService;
    @Mock RagService ragService;

    @InjectMocks ChatService chatService;

    private static IntentResponse detected(Intent intent, String governorate) {
        return new IntentResponse(intent, 0.9, false, null,
                List.of(new Candidate(intent, 0.9), new Candidate(Intent.CONSEIL_GENERAL, 0.05)),
                true, new Entities(governorate), "test", false);
    }

    /** Stubs the module that should answer this intent and returns its expected answer. */
    private ModuleAnswer stubModule(Intent intent) {
        Map<Intent, Function<ChatContext, ModuleAnswer>> modules = Map.of(
                Intent.MALADIE, ctx -> diseaseService.answer(ctx),
                Intent.IRRIGATION, ctx -> irrigationService.answer(ctx),
                Intent.METEO_ALERTE, ctx -> weatherService.answer(ctx),
                Intent.RECOLTE, ctx -> yieldService.answer(ctx),
                Intent.PRIX_VENTE, ctx -> priceService.answer(ctx),
                Intent.COMPTAGE, ctx -> treeCountService.answer(ctx),
                Intent.CONSEIL_GENERAL, ctx -> ragService.answer(ctx));
        ModuleAnswer answer = new ModuleAnswer("reply from " + intent, Map.of("module", intent.name()), true);
        when(modules.get(intent).apply(any())).thenReturn(answer);
        return answer;
    }

    @ParameterizedTest
    @EnumSource(value = Intent.class, names = { "SALUTATION", "HORS_SUJET" }, mode = EnumSource.Mode.EXCLUDE)
    void routesEachIntentToItsModule(Intent intent) {
        when(intentClient.detect("question")).thenReturn(detected(intent, null));
        ModuleAnswer expected = stubModule(intent);

        ChatResponse res = chatService.chat(USER, new ChatRequest("question", null, null));

        assertThat(res.intent()).isEqualTo(intent);
        assertThat(res.reply()).isEqualTo(expected.reply());
        assertThat(res.data()).isEqualTo(expected.data());
        assertThat(res.clarify()).isFalse();
        assertThat(res.suggestions()).isEmpty();
        assertThat(res.mock()).isTrue();
        assertThat(res.generatedBy()).isEqualTo(ChatResponse.TEMPLATE); // no LLM answer -> template
        verify(historyService).record(eq(USER), eq(null), eq(PredictionType.CHAT), any(), eq(res));
    }

    @Test
    void greetingHasAFixedReply() {
        when(intentClient.detect("aslema")).thenReturn(detected(Intent.SALUTATION, null));
        ChatResponse res = chatService.chat(USER, new ChatRequest("aslema", null, null));
        assertThat(res.reply()).isEqualTo(ChatService.GREETING);
        assertThat(res.clarify()).isFalse();
        verifyNoInteractions(diseaseService, irrigationService, weatherService, yieldService, priceService,
                treeCountService, ragService, answerClient);
    }

    @Test
    void offTopicIsPolitelyRefused() {
        when(intentClient.detect("wa9tech el bac?")).thenReturn(detected(Intent.HORS_SUJET, null));
        ChatResponse res = chatService.chat(USER, new ChatRequest("wa9tech el bac?", null, null));
        assertThat(res.reply()).isEqualTo(ChatService.OFF_TOPIC);
        verifyNoInteractions(ragService);
    }

    @Test
    void clarifyAsksTheQuestionAndSuggestsCandidates() {
        String question = "T7eb ta3ref 9adech mn chajra 3andek, walla 9adech bech tjib mn zitoun w zit?";
        when(intentClient.detect(anyString())).thenReturn(new IntentResponse(Intent.RECOLTE, 0.45, true, question,
                List.of(new Candidate(Intent.RECOLTE, 0.45), new Candidate(Intent.COMPTAGE, 0.40),
                        new Candidate(Intent.HORS_SUJET, 0.05)),
                true, new Entities(null), "test", false));

        ChatResponse res = chatService.chat(USER, new ChatRequest("9adech 3andi?", null, null));

        assertThat(res.clarify()).isTrue();
        assertThat(res.reply()).isEqualTo(question);
        assertThat(res.intent()).isEqualTo(Intent.RECOLTE);
        assertThat(res.suggestions()).containsExactly(Intent.RECOLTE, Intent.COMPTAGE); // no "hors_sujet" button
        verifyNoInteractions(yieldService, treeCountService);
    }

    @Test
    void domainGuardSuggestsTheMainTopics() {
        when(intentClient.detect(anyString())).thenReturn(new IntentResponse(Intent.HORS_SUJET, 0.35, true,
                IntentResponse.GENERIC_QUESTION,
                List.of(new Candidate(Intent.HORS_SUJET, 0.35), new Candidate(Intent.MALADIE, 0.30),
                        new Candidate(Intent.SALUTATION, 0.10)),
                false, new Entities(null), "test", false));

        ChatResponse res = chatService.chat(USER, new ChatRequest("zitouni mouch labes", null, null));

        assertThat(res.clarify()).isTrue();
        assertThat(res.suggestions()).startsWith(Intent.MALADIE).doesNotContain(Intent.HORS_SUJET, Intent.SALUTATION)
                .contains(Intent.IRRIGATION, Intent.PRIX_VENTE).doesNotHaveDuplicates();
    }

    @Test
    void forcedIntentSkipsClassification() {
        ModuleAnswer expected = stubModule(Intent.COMPTAGE);
        ChatResponse res = chatService.chat(USER, new ChatRequest("9adech 3andi?", null, Intent.COMPTAGE));
        verify(intentClient, never()).detect(anyString());
        assertThat(res.intent()).isEqualTo(Intent.COMPTAGE);
        assertThat(res.reply()).isEqualTo(expected.reply());
        assertThat(res.clarify()).isFalse();
    }

    @Test
    void intentServiceDownFallsBackToGenericQuestion() {
        when(intentClient.detect(anyString())).thenReturn(IntentResponse.fallback());

        ChatResponse res = chatService.chat(USER, new ChatRequest("9adech nesgi?", null, null));

        assertThat(res.clarify()).isTrue();
        assertThat(res.reply()).isEqualTo(IntentResponse.GENERIC_QUESTION);
        assertThat(res.suggestions()).containsExactly(Intent.MALADIE, Intent.IRRIGATION, Intent.METEO_ALERTE,
                Intent.RECOLTE, Intent.PRIX_VENTE, Intent.COMPTAGE);
        assertThat(res.mock()).isTrue();
    }

    @Test
    void failingModuleGivesATryAgainReply() {
        when(intentClient.detect(anyString())).thenReturn(detected(Intent.PRIX_VENTE, null));
        when(priceService.answer(any())).thenThrow(new AiServiceException(HttpStatus.SERVICE_UNAVAILABLE, "M4 down"));

        ChatResponse res = chatService.chat(USER, new ChatRequest("nbi3 taw?", null, null));

        assertThat(res.reply()).isEqualTo(ChatService.MODULE_DOWN);
        assertThat(res.intent()).isEqualTo(Intent.PRIX_VENTE);
        assertThat(res.clarify()).isFalse();
    }

    @Test
    void llmWritesTheReplyFromTheModuleFacts() {
        when(intentClient.detect(anyString())).thenReturn(detected(Intent.IRRIGATION, null));
        Fact m2 = Fact.of("M2", true, "jours_irrigation_sur_7", 6);
        when(irrigationService.answer(any())).thenReturn(new ModuleAnswer("template reply", "plan", true, List.of(m2)));
        when(answerClient.answer(any())).thenReturn(Optional.of(
                new AnswerClient.Answer("اسقي 6 مرات الجمعة هاذي. (معطيات تجريبية)", "gemini", "gemini-3.5-flash", 900)));

        ChatResponse res = chatService.chat(USER, new ChatRequest("9adech nesgi?", null, null));

        assertThat(res.reply()).isEqualTo("اسقي 6 مرات الجمعة هاذي. (معطيات تجريبية)");
        assertThat(res.generatedBy()).isEqualTo("gemini/gemini-3.5-flash");
        assertThat(res.data()).isEqualTo("plan");
        ArgumentCaptor<AnswerClient.Request> sent = ArgumentCaptor.forClass(AnswerClient.Request.class);
        verify(answerClient).answer(sent.capture());
        assertThat(sent.getValue().question()).isEqualTo("9adech nesgi?");
        assertThat(sent.getValue().facts()).containsExactly(m2);
        assertThat(sent.getValue().draft()).isEqualTo("template reply");
    }

    @Test
    void harvestQuestionIsEnrichedWithPriceFacts() {
        when(intentClient.detect(anyString())).thenReturn(detected(Intent.RECOLTE, null));
        Fact m3 = Fact.of("M3", true, "estimation_parcelle_kg_olives", 7500);
        Fact m4 = Fact.of("M4", true, "conseil", "STORE");
        when(yieldService.answer(any())).thenReturn(new ModuleAnswer("yield", null, true, List.of(m3)));
        when(priceService.answer(any())).thenReturn(new ModuleAnswer("price", null, true, List.of(m4)));

        ChatResponse res = chatService.chat(USER, new ChatRequest("9adech bech njib?", null, null));

        ArgumentCaptor<AnswerClient.Request> sent = ArgumentCaptor.forClass(AnswerClient.Request.class);
        verify(answerClient).answer(sent.capture());
        assertThat(sent.getValue().facts()).containsExactly(m3, m4);
        assertThat(res.reply()).isEqualTo("yield"); // no LLM in this test: template of the main module
    }

    @Test
    void failingComplementaryModuleIsIgnored() {
        when(intentClient.detect(anyString())).thenReturn(detected(Intent.PRIX_VENTE, null));
        Fact m4 = Fact.of("M4", true, "conseil", "SELL_NOW");
        when(priceService.answer(any())).thenReturn(new ModuleAnswer("price", null, true, List.of(m4)));
        when(yieldService.answer(any())).thenThrow(new AiServiceException(HttpStatus.SERVICE_UNAVAILABLE, "M3 down"));

        ChatResponse res = chatService.chat(USER, new ChatRequest("nbi3 taw?", null, null));

        assertThat(res.reply()).isEqualTo("price");
        ArgumentCaptor<AnswerClient.Request> sent = ArgumentCaptor.forClass(AnswerClient.Request.class);
        verify(answerClient).answer(sent.capture());
        assertThat(sent.getValue().facts()).containsExactly(m4);
    }

    @Test
    void governorateDetectedByM5IsPassedToTheModule() {
        when(intentClient.detect(anyString())).thenReturn(detected(Intent.METEO_ALERTE, "beja"));
        stubModule(Intent.METEO_ALERTE);

        chatService.chat(USER, new ChatRequest("fama jlid ghodwa fi beja?", null, null));

        ArgumentCaptor<ChatContext> ctx = ArgumentCaptor.forClass(ChatContext.class);
        verify(weatherService).answer(ctx.capture());
        assertThat(ctx.getValue().governorate()).isEqualTo("beja");
        assertThat(ctx.getValue().location()).hasValueSatisfying(l -> assertThat(l.latitude()).isEqualTo(36.73));
    }
}
