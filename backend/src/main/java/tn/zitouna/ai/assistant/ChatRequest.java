package tn.zitouna.ai.assistant;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * parcelId (optional): answer irrigation / weather / harvest questions for that parcel.
 * forcedIntent (optional): the farmer clicked a suggestion button, skip the classification.
 */
public record ChatRequest(
        @NotBlank @Size(max = 500) String text,
        Long parcelId,
        Intent forcedIntent) {
}
