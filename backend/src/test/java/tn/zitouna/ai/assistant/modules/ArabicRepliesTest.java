package tn.zitouna.ai.assistant.modules;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/** Chat replies are in Arabic script: place names and units used in the template replies. */
class ArabicRepliesTest {

    @Test
    void governorateCitedInTheQuestionIsShownInArabic() {
        var location = new ChatContext(1L, "fama jlid fi beja?", null, "beja").location().orElseThrow();
        assertThat(location.label()).isEqualTo("باجة");
        assertThat(location.governorate()).isEqualTo("beja"); // the modules still get the id
    }

    @Test
    void governorateLookupIgnoresCase() {
        assertThat(Governorates.arabic("Sfax")).isEqualTo("صفاقس");
        assertThat(Governorates.arabic("Sidi Bouzid")).isEqualTo("سيدي بوزيد");
        assertThat(Governorates.coordinates("SFAX")).isPresent();
        assertThat(Governorates.arabic("Atlantis")).isEqualTo("Atlantis");
    }

    @Test
    void priceUnitInArabic() {
        assertThat(PriceChatService.perUnit("TND", "kg")).isEqualTo("دينار للكيلو");
        assertThat(PriceChatService.perUnit("EUR", "l")).isEqualTo("EUR/l");
    }

    @Test
    void frenchModuleTextsAreReplacedByArabicNames() {
        assertThat(WeatherChatService.alertName("FROST")).isEqualTo("خطر جليد");
        assertThat(WeatherChatService.alertName("HEATWAVE")).isEqualTo("سخانة قوية");
        assertThat(DiseaseChatStub.diseaseName("peacock_spot", "Œil de paon")).isEqualTo("عين الطاووس");
        assertThat(DiseaseChatStub.diseaseName("new_label", "Nouvelle maladie")).isEqualTo("Nouvelle maladie");
    }
}
