package tn.zitouna.ai.assistant.modules;

/** Chat intent "recolte" -> M3 (yield forecast). */
public interface YieldService {

    ModuleAnswer answer(ChatContext ctx);
}
