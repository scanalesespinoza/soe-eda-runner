package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record PromoteResponse(
    @JsonProperty("status") String status,
    @JsonProperty("message") String message
) {
}
