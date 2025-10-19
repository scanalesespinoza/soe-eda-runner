package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record PromoteRequest(
    @JsonProperty("modelUri") String modelUri
) {
}
