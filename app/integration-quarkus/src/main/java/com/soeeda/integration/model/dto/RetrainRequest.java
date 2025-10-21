package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

public record RetrainRequest(
    @JsonProperty("datasetPath") String datasetPath,
    @JsonProperty("outPrefix") String outPrefix,
    @JsonProperty("params") Map<String, Object> params
) {
}
