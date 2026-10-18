package tn.zitouna.ai.assistant.modules;

import org.springframework.stereotype.Service;

/** conseil_general -> RAG (M5). STUB until the RAG over the FAO / COI / ministry guides is ready. */
@Service
public class RagChatStub implements RagService {

    @Override
    public ModuleAnswer answer(ChatContext ctx) {
        // TODO(M5): call the RAG endpoint of the M5 service (Chroma + LLM) with ctx.text() and return the
        //  answer with its sources in data.
        return ModuleAnswer.stub("(جواب تجريبي) بعد شوية باش نجاوبك من أدلة FAO و COI ووزارة الفلاحة.");
    }
}
