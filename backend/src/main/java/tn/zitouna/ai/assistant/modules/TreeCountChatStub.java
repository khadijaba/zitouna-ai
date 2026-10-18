package tn.zitouna.ai.assistant.modules;

import java.util.List;

import org.springframework.stereotype.Service;

/** comptage -> M6. STUB: M6 needs a drone / satellite image, which the chat cannot send yet. */
@Service
public class TreeCountChatStub implements TreeCountService {

    @Override
    public ModuleAnswer answer(ChatContext ctx) {
        // TODO(M6): when the chat accepts images, call TreeCountClient.count(image) and answer with treeCount.
        if (ctx.parcel() != null && ctx.parcel().getTreeCount() != null) {
            String reply = "في القطعة « %s » مسجلين %d زيتونة. باش نعاود نحسبهم، ابعثلي تصويرة من الدرون ولا الساتليت في صفحة القطعة."
                    .formatted(ctx.parcel().getName(), ctx.parcel().getTreeCount());
            Fact fact = Fact.of("parcelle", false, "nombre_arbres_enregistre", ctx.parcel().getTreeCount(),
                    "comment_recompter", "envoyer une image drone ou satellite dans la page de la parcelle");
            return new ModuleAnswer(reply, null, true, List.of(fact));
        }
        return ModuleAnswer.stub(
                "ابعثلي تصويرة من الدرون ولا الساتليت في صفحة القطعة، وأنا نحسبلك عدد الزيتون.");
    }
}
