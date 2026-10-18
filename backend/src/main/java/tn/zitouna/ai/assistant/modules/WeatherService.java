package tn.zitouna.ai.assistant.modules;

/** Chat intent "meteo_alerte" -> M2 (frost / heatwave alerts). */
public interface WeatherService {

    ModuleAnswer answer(ChatContext ctx);
}
