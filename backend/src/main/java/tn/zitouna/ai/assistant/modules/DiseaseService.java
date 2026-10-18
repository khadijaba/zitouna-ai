package tn.zitouna.ai.assistant.modules;

/** Chat intent "maladie" -> M1 (leaf diseases). */
public interface DiseaseService {

    ModuleAnswer answer(ChatContext ctx);
}
