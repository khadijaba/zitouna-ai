package tn.zitouna.ai.trees;

import java.util.List;

import tn.zitouna.ai.AiResult;

/** Response of M6 POST /predict. Boxes are in pixels of the uploaded image. */
public record TreeCountResult(
        int treeCount,
        List<Box> boxes,
        String annotatedImageBase64,
        String modelVersion,
        boolean mock) implements AiResult {

    public record Box(double x, double y, double width, double height, double confidence) {
    }
}
