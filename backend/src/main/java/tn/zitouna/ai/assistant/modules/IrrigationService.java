package tn.zitouna.ai.assistant.modules;

/** Chat intent "irrigation" -> M2 (water need). */
public interface IrrigationService {

    ModuleAnswer answer(ChatContext ctx);
}
