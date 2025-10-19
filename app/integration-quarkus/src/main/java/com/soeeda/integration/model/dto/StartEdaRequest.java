package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record StartEdaRequest(
    @JsonProperty("datasetPath") String datasetPath,
    @JsonProperty("outputPath") String outputPath,
    @JsonProperty("outliersCol") String outliersCol
) {
}
