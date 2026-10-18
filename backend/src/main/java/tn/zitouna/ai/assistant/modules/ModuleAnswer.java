package tn.zitouna.ai.assistant.modules;

import java.util.List;

/**
 * Answer of a module to a chat question.
 *
 * @param reply template text for the farmer (derja, arabizi); used as is when no LLM is available
 * @param data  raw module result for the app (charts, tables), or null
 * @param mock  true if the answer is not produced by a trained model yet
 * @param facts compact facts given to the LLM to write a richer reply
 */
public record ModuleAnswer(String reply, Object data, boolean mock, List<Fact> facts) {

    public ModuleAnswer(String reply, Object data, boolean mock) {
        this(reply, data, mock, List.of());
    }

    public static ModuleAnswer stub(String reply) {
        return new ModuleAnswer(reply, null, true);
    }
}
