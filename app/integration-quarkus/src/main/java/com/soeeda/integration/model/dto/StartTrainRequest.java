package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

public record StartTrainRequest(
    @JsonProperty("datasetPath") String datasetPath,
    @JsonProperty("params") Map<String, Object> params
) {
}
