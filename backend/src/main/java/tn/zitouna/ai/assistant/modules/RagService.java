package tn.zitouna.ai.assistant.modules;

/** Chat intent "conseil_general" -> RAG on the agricultural guides (M5). */
public interface RagService {

    ModuleAnswer answer(ChatContext ctx);
}
