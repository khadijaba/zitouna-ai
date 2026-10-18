package tn.zitouna.ai.assistant.modules;

/** Chat intent "prix_vente" -> M4 (price and selling time). */
public interface PriceService {

    ModuleAnswer answer(ChatContext ctx);
}
